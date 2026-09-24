# -*- coding: utf-8 -*-
"""LMStudioClient 의 스트리밍 + 취소(cancel_check) + 한글 인코딩 동작을 mock SSE 서버로 검증한다.

- 스트리밍으로 받아오므로 사용자가 취소하면 연결을 끊어 LM Studio 생성도 중단된다.
- requests 는 text/event-stream 응답의 charset 이 없으면 ISO-8859-1 로 디코딩해
  한글을 mojibake 로 깨뜨린다. 반드시 바이트로 받아 UTF-8 로 직접 디코딩해야 한다.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from studio.integrations.lmstudio import LMStudioClient


def _sse_delta(content_delta):
    """OpenAI/LM Studio 스트리밍 형식의 하나의 SSE data: 줄을 만든다."""
    obj = {"id": "x", "choices": [{"index": 0, "delta": {"content": content_delta}}]}
    return ("data: " + json.dumps(obj, ensure_ascii=False) + "\n\n").encode("utf-8")


SSE_DONE = b"data: [DONE]\n\n"


class _SSEHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _drain_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except Exception:
            length = 0
        if length:
            try:
                self.rfile.read(length)
            except Exception:
                pass

    def do_POST(self):
        srv = self.server
        self._drain_body()
        srv.request_count += 1

        # 후보 retry 를 검증: 첫 요청은 response_format 400 -> 다음 후보로 넘어감
        if getattr(srv, "do_400_first", False) and srv.request_count == 1:
            self.send_response(400)
            self.send_header("Content-Length", "38")
            self.end_headers()
            self.wfile.write(b"response_format not supported by server")
            return

        # 스트리밍을 무시하고 일반 JSON 본문을 보내는 구버전 케이스 검증
        if getattr(srv, "mode", "sse") == "raw_json":
            body = json.dumps({"choices": [{"message": {"content": '{"ok": true}'}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.close_connection = True
            self.end_headers()
            self.wfile.write(body)
            return

        # SSE 스트리밍 (charset 없이 text/event-stream 로 보낸다 - 실제 LM Studio 와 동일)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "close")
        self.close_connection = True
        self.end_headers()
        for delay, payload in getattr(srv, "plan", []):
            if delay:
                time.sleep(delay)
            if payload is None:
                continue
            try:
                self.wfile.write(payload)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                srv.client_disconnected = True
                return
        srv.client_disconnected = getattr(srv, "client_disconnected", False)

    def log_message(self, *args, **kwargs):
        pass


@pytest.fixture
def server():
    s = ThreadingHTTPServer(("127.0.0.1", 0), _SSEHandler)
    s.plan = []
    s.request_count = 0
    s.client_disconnected = False
    s.do_400_first = False
    s.mode = "sse"
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    addr = s.server_address
    try:
        yield {"host": addr[0], "port": addr[1], "server": s}
    finally:
        s.shutdown()
        s.server_close()


def _client(server):
    return LMStudioClient({"host": server["host"], "port": server["port"], "api_path": "/v1"})


def test_chat_json_streams_and_accumulates_content(server):
    """여러 SSE 청크를 누적해 하나의 JSON 문자열이 되어 파싱되는지 확인한다."""
    server["server"].plan = [
        (0.0, _sse_delta('{"ok":')),
        (0.05, _sse_delta(" true}")),
        (0.05, SSE_DONE),
    ]
    client = _client(server)
    start = time.time()
    result = client.chat_json("sys", "user")
    elapsed = time.time() - start
    assert result == {"ok": True}
    assert elapsed < 2.0


def test_korean_survives_streaming(server):
    """한글이 SSE 스트리밍 파싱에서 mojibake 로 깨지지 않는다 (UTF-8 명시 디코딩)."""
    server["server"].plan = [
        (0.0, _sse_delta('{"ok": "안녕, 세상!"}')),
        (0.05, SSE_DONE),
    ]
    client = _client(server)
    result = client.chat_json("sys", "user")
    assert result == {"ok": "안녕, 세상!"}


def test_cancel_between_chunks_raises_interrupted(server):
    """청크 흐름 중 cancel_check 가 True 면 즉시 InterruptedError 가 나고,
    클라이언트가 연결을 닫아 서버가 이를 감지한다 (LM Studio 가 멈추는 신호)."""
    server["server"].plan = [
        (0.0, _sse_delta("chunk1-")),
        (0.2, _sse_delta("x" * 300000)),  # 소켓 버퍼를 채워 서버가 단절을 감지하게 한다
        (0.4, SSE_DONE),
    ]
    client = _client(server)
    flag = {"v": False}

    def setter():
        time.sleep(0.2)
        flag["v"] = True

    threading.Thread(target=setter, daemon=True).start()
    start = time.time()
    with pytest.raises(InterruptedError):
        client.chat_json("sys", "user", cancel_check=lambda: flag["v"])
    elapsed = time.time() - start
    assert elapsed < 2.0
    time.sleep(0.8)
    assert server["server"].client_disconnected is True


def test_cancel_during_stall_raises_interrupted(server):
    """서버가 멈춰 있어도(read timeout) cancel_check 가 깨져서 중단된다."""
    server["server"].plan = [
        (0.0, _sse_delta("chunk1-")),
        (4.0, SSE_DONE),
    ]
    client = _client(server)
    flag = {"v": False}

    def setter():
        time.sleep(0.5)
        flag["v"] = True

    threading.Thread(target=setter, daemon=True).start()
    start = time.time()
    with pytest.raises(InterruptedError):
        client.chat_json("sys", "user", timeout=1, cancel_check=lambda: flag["v"])
    elapsed = time.time() - start
    assert 2.5 <= elapsed <= 4.0
    # 서버가 sleep 중이면(쓰기 없음) 단절을 감지 못할 수 있다.
    # 클라이언트가 stall 도중에도 취소된다는 것(위 InterruptedError)이 이 테스트의 핵심.


def test_response_format_400_retry_then_stream(server):
    """400 response_format 오류 시 다음 후보로 재시도한 뒤 스트리밍 성공한다."""
    server["server"].do_400_first = True
    server["server"].plan = [
        (0.0, _sse_delta('{"ok":')),
        (0.05, _sse_delta(" true}")),
        (0.05, SSE_DONE),
    ]
    client = _client(server)
    result = client.chat_json("sys", "user")
    assert result == {"ok": True}
    assert server["server"].request_count == 2


def test_raw_json_fallback(server):
    """서버가 스트리밍을 무시하고 일반 JSON 본문을 보내도 파싱된다."""
    server["server"].mode = "raw_json"
    client = _client(server)
    result = client.chat_json("sys", "user")
    assert result == {"ok": True}
