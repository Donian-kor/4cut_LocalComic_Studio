# -*- coding: utf-8 -*-
"""ComfyUIClient의 업로드 검증과 wait_for_image 오류/취소 분기를 검증한다."""
import pytest

from studio.integrations.comfyui import ComfyUIClient


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_upload_rejects_missing_empty_and_unsupported_files(tmp_path):
    client = ComfyUIClient({})
    with pytest.raises(ValueError):
        client.upload_image(tmp_path / "nope.png")

    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    with pytest.raises(ValueError):
        client.upload_image(empty)

    bad = tmp_path / "anim.gif"
    bad.write_bytes(b"GIF89a")
    with pytest.raises(ValueError):
        client.upload_image(bad)


def test_wait_for_image_raises_on_error_status(monkeypatch):
    client = ComfyUIClient({})
    payload = {"pid": {
        "status": {"status_str": "error", "completed": False,
                   "messages": [["execution_error", {"exception_message": "boom"}]]},
        "outputs": {},
    }}
    monkeypatch.setattr(
        "studio.integrations.comfyui.requests.get", lambda *a, **k: _Resp(payload)
    )
    with pytest.raises(RuntimeError):
        client.wait_for_image("pid")


def test_wait_for_image_raises_when_completed_false_without_messages(monkeypatch):
    # messages가 없어도 완료 판정이 불가능한 상태는 즉시 오류 (타임아웃까지 대기 방지)
    client = ComfyUIClient({})
    payload = {"pid": {
        "status": {"status_str": "", "completed": False, "messages": []},
        "outputs": {},
    }}
    monkeypatch.setattr(
        "studio.integrations.comfyui.requests.get", lambda *a, **k: _Resp(payload)
    )
    with pytest.raises(RuntimeError):
        client.wait_for_image("pid")


def test_wait_for_image_raises_on_completed_false_with_messages(monkeypatch):
    client = ComfyUIClient({})
    payload = {"pid": {
        "status": {"status_str": "success", "completed": False,
                   "messages": [["execution_error", {}]]},
        "outputs": {},
    }}
    monkeypatch.setattr(
        "studio.integrations.comfyui.requests.get", lambda *a, **k: _Resp(payload)
    )
    with pytest.raises(RuntimeError):
        client.wait_for_image("pid")


def test_cancel_triggers_interrupt_in_worker_thread(monkeypatch):
    client = ComfyUIClient({})
    posts = []
    monkeypatch.setattr(
        "studio.integrations.comfyui.requests.post",
        lambda *a, **k: posts.append(a) or _Resp({}),
    )
    with pytest.raises(InterruptedError):
        client.wait_for_image("pid", cancel_check=lambda: True)
    assert posts, "취소 감지 시 interrupt 요청이 있어야 한다"
    assert "/interrupt" in posts[0][0]


def test_no_outputs_raises_after_grace_polls(monkeypatch):
    client = ComfyUIClient({})
    payload = {"pid": {
        "status": {"status_str": "success", "completed": True, "messages": []},
        "outputs": {},
    }}
    monkeypatch.setattr(
        "studio.integrations.comfyui.requests.get", lambda *a, **k: _Resp(payload)
    )
    with pytest.raises(RuntimeError):
        client.wait_for_image("pid", poll=0)
