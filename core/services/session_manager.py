import copy
import json
import shutil
import threading
import time
import uuid
from pathlib import Path
from core.models.chat import ChatSession


# 직렬화 시 상대경로로 변환/복원할 수 있는 문자열 키들
_PATH_KEYS = {"result_path", "image_path", "output_path", "path"}


class SessionManager:
    """ChatSession의 JSON 저장/복원을 담당한다. UI나 Worker 객체는 저장하지 않는다.

    - 손상된 기록은 건질 수 있는 것만 복구하고, 손상 원본은 sessions.corrupt*.json에 격리한다.
    - 저장은 고유 임시파일 + 원자적 교체로 수행한다.
    - update()는 700ms 디바운스 저장, add()/remove()/flush()는 즉시 저장한다.
    - 저장 파일 안의 경로는 프로젝트 폴더 기준 상대경로로 남기고 로드 시 복원한다.
    """

    SAVE_DEBOUNCE_SECONDS = 0.7

    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        project_path = str(settings_manager.section("general").get("project_path", "projects"))
        self.project_path = settings_manager.resolve_path(project_path)
        self.session_dir = self.project_path / ".sessions"
        self.session_file = self.session_dir / "sessions.json"
        self.sessions = []
        self._lock = threading.RLock()
        self._save_timer = None
        self.load()

    # ------------------------------------------------------------------
    # 경로 변환 (저장: 상대경로 / 로드: 절대경로)
    # ------------------------------------------------------------------
    def _to_relative(self, value):
        try:
            path = Path(str(value))
            if path.is_absolute() and path.is_relative_to(self.project_path):
                return path.relative_to(self.project_path).as_posix()
        except (OSError, ValueError, TypeError):
            pass
        return value

    def _to_absolute(self, value):
        text = str(value or "")
        if text and not Path(text).is_absolute():
            return str(self.project_path / text)
        return text

    def _transform_paths(self, node, fn):
        """dict/list 구조를 순회하며 경로 키 값을 변환한다(복사본 전제)."""
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "panel_paths" and isinstance(value, list):
                    node[key] = [fn(v) if isinstance(v, str) and v else v for v in value]
                elif key in _PATH_KEYS:
                    if isinstance(value, str) and value:
                        node[key] = fn(value)
                else:
                    self._transform_paths(value, fn)
        elif isinstance(node, list):
            for item in node:
                self._transform_paths(item, fn)
        return node

    def load(self):
        self.sessions = []
        if not self.session_file.exists():
            return self.sessions
        try:
            raw = json.loads(self.session_file.read_text(encoding="utf-8"))
        except Exception as exc:
            # 파일 전체가 손상된 경우 원본을 격리해 복구 단서를 남긴 뒤 빈 목록으로 시작한다.
            self._quarantine_file(exc)
            return self.sessions

        corrupt_records = []
        if isinstance(raw, list):
            for index, record in enumerate(raw):
                if not isinstance(record, dict):
                    corrupt_records.append({"index": index, "error": "객체가 아님", "record": record})
                    continue
                try:
                    restored = self._transform_paths(copy.deepcopy(record), self._to_absolute)
                    session = ChatSession.from_dict(restored)
                except Exception as exc:
                    print(f"[SessionManager] 손상된 세션 기록 #{index} 복구 실패: {exc}")
                    corrupt_records.append({"index": index, "error": str(exc), "record": record})
                    continue
                self.sessions.append(session)
        if corrupt_records:
            self._backup_corrupt(corrupt_records)
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

    def _quarantine_file(self, error):
        try:
            self.session_dir.mkdir(parents=True, exist_ok=True)
            backup = self.session_dir / f"sessions.corrupt-{int(time.time())}.json"
            shutil.copy2(self.session_file, backup)
            print(f"[SessionManager] 세션 파일 손상({error}) → 원본 격리: {backup}")
        except OSError:
            pass

    def _backup_corrupt(self, records):
        try:
            self.session_dir.mkdir(parents=True, exist_ok=True)
            target = self.session_dir / "sessions.corrupt.json"
            existing = []
            if target.exists():
                try:
                    parsed = json.loads(target.read_text(encoding="utf-8"))
                    if isinstance(parsed, list):
                        existing = parsed
                except Exception:
                    existing = []
            existing.extend(records)
            tmp = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")
            tmp.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(target)
        except OSError:
            pass

    def save(self):
        with self._lock:
            self.session_dir.mkdir(parents=True, exist_ok=True)
            payload = [
                self._transform_paths(copy.deepcopy(s.to_dict()), self._to_relative)
                for s in list(self.sessions)
            ]
            tmp = self.session_file.with_name(f"{self.session_file.name}.{uuid.uuid4().hex}.tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.session_file)
            for session in list(self.sessions):
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
                data = self._transform_paths(copy.deepcopy(session.to_dict()), self._to_relative)
                tmp = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")
                tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                tmp.replace(target)
        except OSError:
            # 결과 폴더가 삭제/읽기 전용이어도 중앙 세션 인덱스는 유지한다.
            pass

    def _schedule_save(self):
        with self._lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
            timer = threading.Timer(self.SAVE_DEBOUNCE_SECONDS, self._flush)
            timer.daemon = True
            self._save_timer = timer
            timer.start()

    def _flush(self):
        with self._lock:
            self._save_timer = None
        try:
            self.save()
        except Exception as exc:
            print(f"[SessionManager] 세션 저장 실패: {exc}")

    def flush(self):
        """앱 종료 직전 대기 중인 디바운스 저장을 즉시 수행한다."""
        with self._lock:
            if self._save_timer is not None:
                self._save_timer.cancel()
                self._save_timer = None
        self.save()

    def add(self, session):
        with self._lock:
            self.sessions = [s for s in self.sessions if s.id != session.id]
            self.sessions.insert(0, session)
        self.save()

    def update(self, session, immediate=False):
        with self._lock:
            self.sessions = [s for s in self.sessions if s.id != session.id]
            self.sessions.insert(0, session)
        if immediate:
            self.save()
        else:
            self._schedule_save()

    def remove(self, session_id):
        session = self.get(session_id)
        if session is None:
            return False
        # 생성 중 세션은 UI 우회(단축키/코드 호출)에서도 삭제할 수 없도록 방어한다.
        if session.status == "generating":
            return False
        with self._lock:
            self.sessions = [s for s in self.sessions if s.id != session_id]
        self.save()
        return True

    def get(self, session_id):
        return next((s for s in self.sessions if s.id == session_id), None)
