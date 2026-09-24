# -*- coding: utf-8 -*-
"""손상된 세션 기록 격리·복구 및 상대경로 저장/복원을 검증한다."""
import json
from pathlib import Path

from studio.models.chat import ChatSession
from studio.services.session_manager import SessionManager


class FakeSettings:
    def __init__(self, base):
        self.base = Path(base)

    def section(self, name):
        if name == "general":
            return {"project_path": "projects"}
        return {}

    def resolve_path(self, value):
        path = Path(value)
        return path if path.is_absolute() else self.base / path


def _write_sessions(tmp_path, payload_text):
    sessions_dir = tmp_path / "projects" / ".sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    (sessions_dir / "sessions.json").write_text(payload_text, encoding="utf-8")
    return sessions_dir


GOOD = {
    "id": "good",
    "title": "좋은 세션",
    "messages": [],
    "status": "idle",
    "result_path": "",
    "panel_paths": [],
}


def test_corrupt_record_is_isolated_and_others_load(tmp_path):
    payload = json.dumps([GOOD, {"id": "bad", "master_seed": "not-an-int"}], ensure_ascii=False)
    sessions_dir = _write_sessions(tmp_path, payload)

    manager = SessionManager(FakeSettings(tmp_path))

    ids = [s.id for s in manager.sessions]
    assert "good" in ids
    assert "bad" not in ids
    # 손상 기록은 격리 백업으로 복구 단서를 남긴다
    corrupt = sessions_dir / "sessions.corrupt.json"
    assert corrupt.exists()
    records = json.loads(corrupt.read_text(encoding="utf-8"))
    assert records and records[0]["index"] == 1


def test_file_level_corruption_is_quarantined(tmp_path):
    sessions_dir = _write_sessions(tmp_path, "{this is not json")

    manager = SessionManager(FakeSettings(tmp_path))

    assert manager.sessions == []
    backups = list(sessions_dir.glob("sessions.corrupt-*.json"))
    assert backups, "손상 원본이 격리 백업되어야 한다"
    assert backups[0].read_text(encoding="utf-8") == "{this is not json"


def test_paths_are_stored_relative_and_restored_absolute(tmp_path):
    manager = SessionManager(FakeSettings(tmp_path))
    session = ChatSession(id="s1", title="t")
    run_dir = manager.project_path / "2026-01-01"
    session.result_path = str(run_dir / "final_4cut.png")
    session.panel_paths = [str(run_dir / "panel_1.png")]
    session.comic_data = {"panels": [{"index": 1, "image_path": str(run_dir / "panel_1.png")}]}

    manager.add(session)  # 즉시 저장

    raw = json.loads(manager.session_file.read_text(encoding="utf-8"))
    record = raw[0]
    assert record["result_path"] == "2026-01-01/final_4cut.png"
    assert record["panel_paths"] == ["2026-01-01/panel_1.png"]
    assert record["comic_data"]["panels"][0]["image_path"] == "2026-01-01/panel_1.png"

    reloaded = SessionManager(FakeSettings(tmp_path))
    restored = reloaded.get("s1")
    assert restored is not None
    assert restored.result_path == str(manager.project_path / "2026-01-01" / "final_4cut.png")
    assert restored.panel_paths == [str(manager.project_path / "2026-01-01" / "panel_1.png")]


def test_generating_status_recovers_and_flush_commits_debounced_change(tmp_path):
    _write_sessions(tmp_path, json.dumps([dict(GOOD, status="generating")], ensure_ascii=False))

    manager = SessionManager(FakeSettings(tmp_path))
    assert manager.sessions[0].status == "cancelled"

    # 디바운스 update 변경분은 flush()로 즉시 커밋된다
    manager.sessions[0].title = "바뀐 제목"
    manager.update(manager.sessions[0])
    manager.flush()
    raw = json.loads(manager.session_file.read_text(encoding="utf-8"))
    assert raw[0]["title"] == "바뀐 제목"