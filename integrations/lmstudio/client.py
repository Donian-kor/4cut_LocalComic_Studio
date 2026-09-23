import json
import re
import socket

import requests

try:  # urllib3는 requests 의 필수 의존이므로 항상 존재한다.
    import urllib3.exceptions as _urllib3_exc
except Exception:  # pragma: no cover - 방어적
    _urllib3_exc = None


class _ResponseFormatUnsupported(RuntimeError):
    """LM Studio가 response_format을 거부했을 때(400) 다음 후보로 넘어가기 위한 신호."""


class LMStudioClient:
    # 최신 LM Studio 서버는 response_format.type 으로 'json_schema' 와 'text' 만 허용한다.
    # (구버전에서 쓰던 'json_object' 는 400 Bad Request 로 거부된다.)
    # 스키마를 지정하지 않은 호출도 JSON 객체를 받도록 아래 기본 스키마를 사용한다.
    _DEFAULT_JSON_SCHEMA = {"type": "object"}

    def __init__(self, settings):
        self.settings = dict(settings)

    @property
    def base_url(self):
        s = self.settings
        host = str(s.get("host", "127.0.0.1")).strip()
        api = str(s.get("api_path", "/v1")).strip().rstrip("/") or "/v1"
        return f"http://{host}:{int(s.get('port', 1234))}{api}"

    def test_connection(self, timeout=3):
        r = requests.get(self.base_url + "/models", timeout=timeout)
        r.raise_for_status()
        return r.json()

    def list_models(self, timeout=3):
        r = requests.get(self.base_url + "/models", timeout=timeout)
        r.raise_for_status()
        data = r.json()
        items = data.get("data", []) if isinstance(data, dict) else data
        return [str(item["id"]) for item in items if isinstance(item, dict) and item.get("id")]

    def chat_json(self, system_prompt, user_prompt, timeout=180, schema=None, schema_name="response", cancel_check=None):
        """채팅 완성을 요청하고 JSON 객체로 파싱해 돌려준다.

        schema 를 주면 그 구조를 강제하고, 주지 않으면 JSON 객체 아무거나 받는다.
        cancel_check 가 주어졌고 True 를 반환하면 요청을 즉시 중단한다 (InterruptedError).
        스트리밍으로 받아오므로 사용자가 취소해도 LM Studio 가 생성을 중단한다.
        """
        payload = {
            "model": self.settings.get("model") or "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
        }
        content = self._request_content(payload, schema, schema_name, timeout, cancel_check)
        if not isinstance(content, str):
            raise ValueError("LM Studio의 content가 문자열이 아닙니다.")
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"LM Studio가 유효한 JSON을 반환하지 않았습니다: {e}") from e

    def _response_format_candidates(self, schema, schema_name):
        """서버 버전 차이를 흡수하기 위해 시도할 response_format 목록."""
        candidates = []
        if schema:
            candidates.append({
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            })
        candidates.append({
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": False, "schema": self._DEFAULT_JSON_SCHEMA},
        })
        candidates.append({"type": "json_object"})  # 구버전 LM Studio 호환
        candidates.append({"type": "text"})
        candidates.append(None)  # response_format 자체를 보내지 않음
        return candidates

    @staticmethod
    def _streaming_socket_timeout(timeout):
        """connect / read 타임아웃을 계산한다.

        read 타임아웃을 짧게 잡아 cancel_check 를 주기적으로 실행할 수 있도록 한다.
        (긴 read 타임아웃이면 스트림이 잠시 멈춰도 취소가 무시된다.)
        """
        connect_timeout = 5
        if isinstance(timeout, (int, float)) and timeout > 0:
            read_timeout = min(30, max(3, int(timeout)))
        else:
            read_timeout = 10
        return (connect_timeout, read_timeout)

    def _request_content(self, payload, schema, schema_name, timeout, cancel_check=None):
        """response_format 을 바꿔가며 스트리밍으로 content 문자열을 얻어낸다.

        400 응답이 response_format 문제라면 다음 후보로 넘어가고,
        그 밖의 400 은 원래 오류를 그대로 올린다.
        cancel_check 가 True 를 반환하면 즉시 요청을 중단한다 (InterruptedError).
        """
        last_error = None
        for response_format in self._response_format_candidates(schema, schema_name):
            if cancel_check and cancel_check():
                raise InterruptedError("LM Studio 요청이 취소되었습니다.")
            body = dict(payload)
            if response_format is not None:
                body["response_format"] = response_format
            try:
                return self._stream_chat(body, timeout, cancel_check)
            except _ResponseFormatUnsupported as e:
                last_error = str(e) or "400 Bad Request"
                continue
        raise RuntimeError(f"LM Studio가 response_format을 지원하지 않습니다: {last_error}")

    def _stream_chat(self, body, timeout, cancel_check=None):
        """stream=True 로 채팅을 요청하고 SSE 청크를 누적해 content 문자열을 반환한다.

        cancel_check 가 True 를 반환하면 응답 스트림을 닫고(서버가 생성을 중단하도록)
        InterruptedError 를 발생시킨다.
        """
        stream_body = dict(body)
        stream_body["stream"] = True
        sock_timeout = self._streaming_socket_timeout(timeout)
        try:
            r = requests.post(
                self.base_url + "/chat/completions",
                json=stream_body,
                timeout=sock_timeout,
                stream=True,
            )
        except requests.RequestException as e:
            raise RuntimeError(f"LM Studio 챗 요청 실패: {e}") from e

        # 400 응답은 스트리밍 시작 전에 반환되므로 여기서 처리한다.
        if r.status_code == 400:
            text = _read_response_text(r)
            if "response_format" in text.lower():
                raise _ResponseFormatUnsupported(text.strip() or "400 Bad Request")
            r.raise_for_status()
        r.raise_for_status()

        try:
            content = self._read_sse_content(r, cancel_check)
        except InterruptedError:
            # 소켓을 닫아 LM Studio 가 생성을 중단하도록 신호를 보낸다.
            r.close()
            raise
        except Exception:
            r.close()
            raise
        return content

    def _read_sse_content(self, r, cancel_check=None):
        """SSE 스트림에서 data: 줄을 누적해 content 문자열을 반환한다.

        - cancel_check 가 True 이면 즉시 InterruptedError 를 발생시킨다.
        - 소켓 read 타임아웃이면(아직 데이터가 없을 뿐) 루프를 계속 돌아 기다린다.
        """
        buffer = ""
        raw_lines = []
        # decode_unicode=False 로 바이트 그대로 받아 UTF-8로 명시 디코딩한다.
        # (requests는 text/event-stream 응답의 charset 을 모르면 ISO-8859-1 로
        #  디코딩해 한글이 mojibake 로 깨진다. 반드시 UTF-8 로 직접 디코딩할 것.)
        lines = r.iter_lines(chunk_size=8192, decode_unicode=False)
        while True:
            if cancel_check and cancel_check():
                raise InterruptedError("LM Studio 요청이 취소되었습니다.")
            try:
                raw = next(lines)
            except StopIteration:
                break
            except Exception as exc:
                if _is_read_timeout(exc):
                    # read 타임아웃: 데이터가 아직 안 왔을 뿐 오류가 아니다. 계속 기다린다.
                    continue
                r.close()
                raise
            if isinstance(raw, bytes):
                line = raw.decode("utf-8", errors="replace")
            else:
                line = str(raw)
            raw_lines.append(line)
            line = line.strip()
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            if not data:
                continue
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = obj.get("choices") or []
            if choices:
                delta = (choices[0].get("delta") or {}).get("content")
                if delta is not None:
                    buffer += str(delta)
        if not buffer:
            # 서버가 스트리밍을 무시하고 일반 응답을 보냈다면 raw body를 JSON으로 파싱한다.
            raw = "\n".join(raw_lines).strip()
            if raw:
                try:
                    obj = json.loads(raw)
                    content = ((obj.get("choices") or [{}])[0].get("message") or {}).get("content")
                    if isinstance(content, str):
                        return content
                except json.JSONDecodeError:
                    pass
            raise RuntimeError("LM Studio 스트리밍 응답에서 content를 받지 못했습니다.")
        return buffer


def _is_read_timeout(exc):
    """스트리밍 read 중 read 타임아웃인지 판별한다 (재개 가능한 경미한 타임아웃)."""
    if isinstance(exc, (requests.exceptions.ReadTimeout, TimeoutError)):
        return True
    try:
        if isinstance(exc, socket.timeout):
            return True
    except Exception:
        pass
    if _urllib3_exc is not None and isinstance(exc, _urllib3_exc.ReadTimeoutError):
        return True
    # requests' iter_content 가 urllib3 ReadTimeoutError 를 ConnectionError 로 감싸서 던진다.
    if isinstance(exc, requests.exceptions.ConnectionError):
        cause = exc.args[0] if exc.args else None
        if cause is not None:
            if _urllib3_exc is not None and isinstance(cause, _urllib3_exc.ReadTimeoutError):
                return True
            if "timed out" in str(cause).lower():
                return True
    return False


def _read_response_text(r):
    """stream=True 응답의 본문 텍스트를 안전하게 읽는다 (주로 400 오류 본문)."""
    try:
        return r.text
    except Exception:
        try:
            return r.content.decode("utf-8", errors="replace")
        except Exception:
            return ""
