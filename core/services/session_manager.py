import json
from pathlib import Path
from core.models.chat import ChatSession


class SessionManager:
    """ChatSession의 JSON 저장/복원을 담당한다. UI나 Worker 객체는 저장하지 않는다."""

    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        project_path = str(settings_manager.section("general").get("project_path", "projects"))
        self.project_path = settings_manager.resolve_path(project_path)
        self.session_dir = self.project_path / ".sessions"
        self.session_file = self.session_dir / "sessions.json"
        self.sessions = []
        self.load()

    def load(self):
        self.sessions = []
        if not self.session_file.exists():
            return self.sessions
        try:
            raw = json.loads(self.session_file.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                self.sessions = [ChatSession.from_dict(x) for x in raw if isinstance(x, dict)]
        except Exception:
            self.sessions = []
        # Worker/QThread는 앱 프로세스에만 존재하므로 재시작 후 "generating" 상태를
        # 영속적으로 남겨 삭제를 막지 않도록 안전하게 복구한다.
        changed = False
        for session in self.sessions:
            if session.status == "generating":
                session.status = "cancelled"
                session.error_message = "앱 재시작으로 진행 중이던 생성은 중단되었습니다."
                changed = True
        self.sessions.sort(key=lambda s: s.updated_at, reverse=True)
        if changed:
            self.save()
        return self.sessions

    def save(self):
        self.session_dir.mkdir(parents=True, exist_ok=True)
        payload = [s.to_dict() for s in self.sessions]
        tmp = self.session_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.session_file)
        for session in self.sessions:
            self._write_project_snapshot(session)

    def _write_project_snapshot(self, session):
        if not session.result_path:
            return
        result = Path(session.result_path)
        if not result.is_absolute():
            result = self.settings_manager.resolve_path(result)
        folder = result.parent
        try:
            if folder.exists():
                target = folder / "session.json"
                tmp = target.with_suffix(".tmp")
                tmp.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
                tmp.replace(target)
        except OSError:
            # 결과 폴더가 삭제/읽기 전용이어도 중앙 세션 인덱스는 유지한다.
            pass

    def add(self, session):
        self.sessions = [s for s in self.sessions if s.id != session.id]
        self.sessions.insert(0, session)
        self.save()

    def update(self, session):
        self.add(session)

    def remove(self, session_id):
        session = self.get(session_id)
        if session is None:
            return False
        # 생성 중 세션은 UI 우회(단축키/코드 호출)에서도 삭제할 수 없도록 방어한다.
        if session.status == "generating":
            return False
        self.sessions = [s for s in self.sessions if s.id != session_id]
        self.save()
        return True

    def get(self, session_id):
        return next((s for s in self.sessions if s.id == session_id), None)
