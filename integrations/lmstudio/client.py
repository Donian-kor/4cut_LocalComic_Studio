import json
import re
import requests


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

    def chat_json(self, system_prompt, user_prompt, timeout=180, schema=None, schema_name="response"):
        """채팅 완성을 요청하고 JSON 객체로 파싱해 돌려준다.

        schema 를 주면 그 구조를 강제하고, 주지 않으면 JSON 객체 아무거나 받는다.
        """
        payload = {
            "model": self.settings.get("model") or "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
        }
        content = self._request_content(payload, schema, schema_name, timeout)
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

    def _request_content(self, payload, schema, schema_name, timeout):
        """response_format 을 바꿔가며 content 문자열을 얻어낸다.

        400 응답이 response_format 문제라면 다음 후보로 넘어가고,
        그 밖의 400 은 원래 오류를 그대로 올린다.
        """
        last_error = None
        for response_format in self._response_format_candidates(schema, schema_name):
            body = dict(payload)
            if response_format is not None:
                body["response_format"] = response_format
            r = requests.post(self.base_url + "/chat/completions", json=body, timeout=timeout)
            if r.status_code == 400 and "response_format" in r.text.lower():
                last_error = r.text.strip() or "400 Bad Request"
                continue
            r.raise_for_status()
            try:
                return r.json()["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e:
                raise RuntimeError(f"LM Studio 응답 형식이 예상과 다릅니다: {e}") from e
        raise RuntimeError(f"LM Studio가 response_format을 지원하지 않습니다: {last_error}")
