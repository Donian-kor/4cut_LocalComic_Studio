import inspect
import logging
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox

from studio.core.presets import ART_STYLE_PRESETS, STYLE_PRESETS
from studio.models.chat import ChatMessageData, ChatSession
from studio.models.comic import Comic
from studio.services.session_manager import SessionManager
from studio.workers.comic_worker import ComicWorker
from studio.workers.panel_regeneration_worker import PanelRegenerationWorker

logger = logging.getLogger(__name__)


class MainController(QObject):
    """세션 상태, 생성 파이프라인, worker 흐름을 담당한다.

    MainWindow/ChatViewManager는 화면만 다루고, 세션의 실제 변경은 이 클래스가
    수행한다. UI는 `window.show_*` 계열 메서드로만 갱신한다.
    """

    def __init__(self, main_window, service_factory, session_manager=None):
        super().__init__(main_window)
        self.window = main_window
        self.service_factory = service_factory
        self.session_manager = session_manager or SessionManager(main_window.settings_manager)
        self.service = None
        self.active_worker = None
        self.active_message_id = None
        self.active_session_id = None
        self.last_idea = ""
        self.last_style_prompt = ""
        self.last_mood = "자동"
        self.last_art_style = "캐주얼 만화"
        self._is_revising = False
        self._operation = ""
        self._active_panel_index = None
        self._active_panel_revision = ""
        self._active_panel_message_id = None

        self.window.bind_controller(self)
        main_window.generationRequested.connect(self.handle_composer_message)
        main_window.cancelRequested.connect(self.cancel_generation)
        main_window.regenerateRequested.connect(self.regenerate)
        main_window.panelRegenerateRequested.connect(self.regenerate_panel)
        main_window.panelRevisionRequested.connect(self.revise_panel)
        main_window.settingsApplied.connect(self.settings_changed)

    # ----- session operations -----
    def flush_sessions(self):
        """앱 종료 직전 대기 중인 세션 저장을 커밋한다."""
        self.session_manager.flush()

    def initialize(self):
        if not self.session_manager.sessions:
            self.new_chat(auto=True)
        else:
            self.open_session(self.session_manager.sessions[0].id)
        self.window.refresh_server_status()

    def get_session(self, session_id=None):
        if session_id:
            return self.session_manager.get(session_id)
        current_id = getattr(self.window.current_session, "id", None)
        return self.session_manager.get(current_id) if current_id else None

    def new_chat(self, auto=False):
        current = self.get_session()
        if current and not auto and not current.messages:
            self.open_session(current.id)
            return current
        session = ChatSession()
        session.add_message(ChatMessageData(
            role="ai",
            kind="text",
            text="안녕하세요! 아이디어를 입력하면 스토리부터 4컷 완성까지 도와드릴게요.",
        ))
        self.session_manager.add(session)
        self._set_current_session(session)
        self.window.composer.idea.clear()
        self.window.composer.load_session_options(session)
        self.window.composer.set_busy(False)
        self.window.statusBar().showMessage("새 대화가 시작되었습니다.")
        return session

    def open_session(self, session_id):
        session = self.session_manager.get(session_id)
        if session is None:
            return None
        self._set_current_session(session)
        self.window.composer.load_session_options(session)
        self.window.composer.idea.clear()
        self.window.composer.set_busy(self.active_worker is not None)
        self.window.statusBar().showMessage(
            "현재 대화에서 생성 중입니다." if session.status == "generating" else "대화를 열었습니다.",
            2000,
        )
        return session

    def _set_current_session(self, session):
        self.window.current_session = session
        self.window.chat_view.set_current_session(session)
        self.window.chat_view.render_session(session)
        self.window._refresh_sidebar()

    def delete_session(self, session_id):
        session = self.session_manager.get(session_id)
        if not session:
            return False
        if session.status == "generating":
            self.window.info_message("삭제할 수 없음", "생성 중인 대화는 생성이 끝나거나 취소될 때까지 삭제할 수 없습니다.")
            return False
        if not self.window.confirm_delete_session(session.title):
            return False
        if not self.session_manager.remove(session_id):
            return False
        if getattr(self.window.current_session, "id", None) == session_id:
            next_session = self.session_manager.sessions[0] if self.session_manager.sessions else None
            if next_session:
                self.open_session(next_session.id)
            else:
                self.new_chat()
        self.window._refresh_sidebar()
        return True

    def rename_session(self, session_id, title):
        session = self.session_manager.get(session_id)
        if not session or session.status == "generating":
            return False
        clean = " ".join(title.replace("⟳", "").replace("!", "").replace("·", "").split())[:40]
        if not clean:
            return False
        session.title = clean
        session.touch()
        self.session_manager.update(session)
        if getattr(self.window.current_session, "id", None) == session.id:
            self.window.statusBar().showMessage(f"대화 이름을 '{clean}'으로 변경했습니다.", 2500)
        self.window._refresh_sidebar()
        return True

    def ensure_user_message(self, text, mood, art_style, idea_value=None, update_title=True):
        session = self.get_session()
        if session is None:
            session = self.new_chat()
        message = ChatMessageData(role="user", kind="text", text=text, mood=mood, art_style=art_style)
        session.add_message(message)
        session.idea = idea_value if idea_value is not None else text
        session.mood = mood
        session.art_style = art_style
        if update_title:
            session.set_title_from_idea(text)
        self.session_manager.update(session)
        self.window.chat_view.append_user_message(text, mood, art_style)
        return session

    # ----- setup / cancellation -----
    def settings_changed(self):
        if self.active_worker and self.active_worker.isRunning():
            return
        try:
            self.service = self.service_factory()
        except Exception:
            self.service = None
            logger.exception("AI 생성 설정을 준비하지 못했습니다.")
            self.window.warning_message(
                "설정 확인 필요",
                "AI 생성 설정을 준비하지 못했습니다. 설정을 확인한 뒤 다시 시도해 주세요.",
            )

    def _server_ready(self):
        return all(getattr(self.window, "_server_state", (False, False)))

    def handle_composer_message(self, text, style_prompt, mood, art_style):
        if self.active_worker and self.active_worker.isRunning():
            self.window.statusBar().showMessage("현재 다른 대화에서 생성 중입니다. 생성이 끝난 뒤 새 요청을 보내 주세요.", 3000)
            return
        text = text.strip()
        if not text:
            return
        session = self.get_session()
        has_result = bool(session and session.result_path and session.status in {"completed", "failed", "cancelled"})
        if has_result:
            self.revise(text, style_prompt=style_prompt, mood=mood, art_style=art_style)
        else:
            self.start_generation(text, style_prompt, mood, art_style)

    def mark_generating(self, session_id=None):
        session = self.get_session(session_id)
        if session is not None:
            session.status = "generating"
            session.error_message = ""
            session.touch()
            self.session_manager.update(session)
            self.active_session_id = session.id
            self.window._generating_session_id = session.id
        self.window._set_status_label("● AI 작업 중", "busy")
        self.window.set_generation_busy(True)
        self.window._refresh_sidebar()

    def _new_generation_message(self, session, initial, phase, panel_index=0):
        data = ChatMessageData(
            role="ai",
            kind="generation",
            text=initial,
            metadata={"phase": phase, "panel_index": int(panel_index or 0), "current": 0},
        )
        session.add_message(data)
        self.session_manager.update(session)
        self.window.show_generation_message(data)
        self.window.composer.set_busy(True)
        return data.id

    def start_generation(self, idea, style_prompt, mood, art_style, display_text=None, update_title=True, add_user=True,
                         service=None, character_prompt=None):
        if self.active_worker and self.active_worker.isRunning():
            return
        idea = idea.strip()
        if not idea:
            return
        if add_user:
            session = self.ensure_user_message(
                display_text if display_text is not None else idea,
                mood, art_style, idea_value=idea, update_title=update_title,
            )
        else:
            session = self.get_session()
            if session is None:
                session = self.ensure_user_message(idea, mood, art_style)
        if not self._server_ready():
            self.window.add_ai_text("LM Studio와 ComfyUI가 모두 연결되어야 4컷 만화를 만들 수 있어요. 설정에서 연결을 확인해 주세요.")
            self.window.refresh_server_status()
            return
        try:
            if service is not None:
                self.service = service
            else:
                self.service = self.service_factory()
        except Exception:
            logger.exception("생성 설정을 준비하지 못했습니다.")
            self.window.add_ai_text("생성 설정을 준비하지 못했습니다. 설정을 확인한 뒤 다시 시도해 주세요.")
            return

        self.last_idea = idea
        self.last_style_prompt = style_prompt
        self.last_mood = mood
        self.last_art_style = art_style
        self.active_session_id = session.id
        self.mark_generating(session.id)
        self.active_message_id = self._new_generation_message(session, "스토리 구성 중…", "story")

        worker = ComicWorker(self.service, idea, style_prompt, character_prompt=character_prompt or "")
        self.active_worker = worker
        worker.progress.connect(self._on_progress)
        worker.planned.connect(self._on_planned)
        worker.panel_started.connect(self._on_panel_started)
        worker.panel_completed.connect(self._on_panel_completed)
        worker.compose_started.connect(self._on_compose_started)
        worker.finished_comic.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.cancelled.connect(self._on_cancelled)
        worker.finished.connect(self._release_worker)
        worker.start()

    def _target_session(self):
        return self.session_manager.get(self.active_session_id) if self.active_session_id else None

    def _on_planned(self, comic):
        session = self._target_session()
        if session is None or comic is None:
            return
        session.master_seed = int(getattr(comic, "master_seed", 0) or 0)
        session.character_prompt = str(getattr(comic, "character_prompt", "") or "")
        session.style_prompt = str(getattr(comic, "style_prompt", "") or "")
        session.generation_config = dict(getattr(comic, "generation_config", {}) or {})
        session.comic_data = comic.to_dict()
        item = self._message(session, self.active_message_id)
        summary = self._story_summary(comic, session)
        if item is not None:
            item.kind = "story_plan"
            item.text = "스토리 계획"
            item.metadata = summary
            session.touch()
        self.session_manager.update(session)
        self.window.show_story_plan(self.active_message_id, summary)
        self.active_message_id = None

    def _message(self, session, message_id):
        if not session or not message_id:
            return None
        return next((m for m in session.messages if m.id == message_id), None)

    def _on_progress(self, message, current, total):
        if not self.active_message_id:
            return
        session = self._target_session()
        item = self._message(session, self.active_message_id)
        if item is not None:
            item.text = message
            item.metadata["current"] = int(current or 0)
            session.touch()
            self.session_manager.update(session)
        self.window.update_generation(self.active_message_id, message, current, total)

    def _on_panel_started(self, index):
        session = self._target_session()
        if session is None:
            return
        message = f"{index}컷 이미지 생성 중"
        if self.active_message_id is None:
            self.active_message_id = self._new_generation_message(session, message, "panel", index)
        else:
            item = self._message(session, self.active_message_id)
            if item is not None:
                item.text = message
                item.metadata.update({"phase": "panel", "panel_index": int(index), "current": max(0, int(index) - 1)})
                session.touch()
                self.session_manager.update(session)
            self.window.begin_panel_generation(self.active_message_id, index, message)

    def _on_compose_started(self):
        session = self._target_session()
        if session is None:
            return
        message = "4컷 합성 중"
        if self.active_message_id is None:
            self.active_message_id = self._new_generation_message(session, message, "compose")
        else:
            item = self._message(session, self.active_message_id)
            if item is not None:
                item.text = message
                item.metadata.update({"phase": "compose", "current": 4})
                session.touch()
                self.session_manager.update(session)
            self.window.begin_final_composition(self.active_message_id, message)

    def _on_panel_completed(self, index, path, dialogue_status=""):
        message_id = self.active_message_id
        session = self._target_session()
        comic = getattr(self.active_worker, "comic", None) if self.active_worker else None
        if not message_id or session is None:
            return
        dialogue = ""
        if comic is not None:
            session.comic_data = comic.to_dict()
            panels = getattr(comic, "panels", [])
            if 1 <= index <= len(panels):
                dialogue = str(getattr(panels[index - 1], "dialogue", "") or "")
        while len(session.panel_paths) < index:
            session.panel_paths.append("")
        session.panel_paths[index - 1] = path or ""
        item = self._message(session, message_id)
        if item is not None:
            item.kind = "panel_result"
            item.text = self._panel_result_text(index, dialogue_status)
            item.metadata = {
                "panel_index": int(index),
                "path": path or "",
                "dialogue": dialogue or "",
                "dialogue_status": str(dialogue_status or ""),
            }
        session.touch()
        self.session_manager.update(session)
        self.window.complete_panel_generation(message_id, index, path, dialogue, dialogue_status)
        self.active_message_id = None

    def _on_finished(self, comic):
        message_id = self.active_message_id
        self.active_message_id = None
        session = self._target_session()
        was_revising = self._is_revising
        self._is_revising = False
        if session is not None:
            self._commit_completed_session(session, message_id, comic)
            self.session_manager.update(session)
            self.window.finish_generation(message_id, comic, session)
        self.last_idea = comic.idea or self.last_idea
        self.active_session_id = None
        if was_revising:
            self.window.statusBar().showMessage("수정 요청을 반영해 4컷을 다시 완성했습니다.", 4000)

    def _commit_completed_session(self, session, message_id, comic):
        session.status = "completed"
        session.error_message = ""
        session.result_path = comic.output_path or ""
        session.master_seed = int(getattr(comic, "master_seed", session.master_seed) or 0)
        session.character_prompt = str(getattr(comic, "character_prompt", session.character_prompt) or "")
        session.style_prompt = str(getattr(comic, "style_prompt", session.style_prompt) or "")
        session.generation_config = dict(getattr(comic, "generation_config", session.generation_config) or {})
        session.comic_data = comic.to_dict() if hasattr(comic, "to_dict") else session.comic_data
        session.panel_paths = [p.image_path for p in getattr(comic, "panels", []) if getattr(p, "image_path", "")]
        item = self._message(session, message_id)
        if item and item.kind == "generation":
            item.text = "4컷 생성이 완료되었습니다."
            item.metadata["phase"] = "compose"
            item.metadata["current"] = 4
        session.add_message(ChatMessageData(
            role="ai",
            kind="result",
            text="완성",
            metadata={"result_path": session.result_path},
        ))
        session.touch()

    def _on_failed(self, message):
        message_id = self.active_message_id
        self.active_message_id = None
        was_revising = self._is_revising
        self._is_revising = False
        session = self._target_session()
        if session is not None:
            session.status = "failed"
            session.error_message = str(message)
            item = self._message(session, message_id)
            if item:
                item.text = str(message)
                item.metadata["failed"] = True
            session.touch()
            self.session_manager.update(session)
            self.window.fail_generation(message_id, str(message), session)
        if was_revising:
            self.window.add_ai_text("수정 요청을 반영하지 못했습니다. 다시 시도해 주세요.")
        self.active_session_id = None

    def _on_cancelled(self):
        message_id = self.active_message_id
        self.active_message_id = None
        self._is_revising = False
        session = self._target_session()
        if session is not None:
            session.status = "cancelled"
            item = self._message(session, message_id)
            if item:
                item.text = "생성이 취소되었습니다."
                item.metadata["cancelled"] = True
            session.touch()
            self.session_manager.update(session)
            self.window.cancel_generation_ui(message_id, session)
        self.active_session_id = None

    def _release_worker(self):
        worker = self.sender()
        if worker is self.active_worker:
            self.active_worker = None
        if worker is not None:
            worker.deleteLater()

    def _comic_from_session(self, session):
        data = getattr(session, "comic_data", {}) or {}
        if not data:
            return None
        try:
            return Comic.from_dict(data)
        except Exception:
            logger.exception("세션에 저장된 만화 데이터를 복원하지 못했습니다.")
            return None

    def _service_for_session(self, session):
        model_id = str((session.generation_config or {}).get("id", "") or "").strip()
        # 호출 전에 시그니처로 인자를 받는지 확인한다. 예외 폴백을 쓰면
        # 팩토리 내부 TypeError까지 삼켜 원인을 마스킹한다.
        if self._factory_accepts_model_id():
            return self.service_factory(model_id or None)
        return self.service_factory()

    def _factory_accepts_model_id(self):
        try:
            params = inspect.signature(self.service_factory).parameters.values()
        except (TypeError, ValueError):
            # 시그니처를 알 수 없는 callable은 표준 형태(model_id 인자)로 간주한다.
            return True
        return any(
            p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.VAR_POSITIONAL)
            for p in params
        )

    def regenerate_panel(self, panel_index):
        self._start_panel_regeneration(panel_index, "")

    def revise_panel(self, panel_index, revision):
        self._start_panel_regeneration(panel_index, revision or "")

    def _start_panel_regeneration(self, panel_index, revision):
        if self.active_worker and self.active_worker.isRunning():
            return
        session = self.get_session()
        if not session or session.status == "generating":
            return
        comic = self._comic_from_session(session)
        if comic is None or not (1 <= int(panel_index) <= len(comic.panels)):
            self.window.warning_message("재생성할 수 없음", "저장된 컷 생성 정보가 없어 해당 컷을 다시 만들 수 없습니다.")
            return
        try:
            service = self._service_for_session(session)
            if session.result_path:
                service.set_run_folder(Path(session.result_path).parent)
        except Exception:
            logger.exception("기존 생성 설정을 준비하지 못했습니다.")
            self.window.warning_message("생성 설정 확인 필요", "기존 생성 설정을 준비하지 못했습니다. 설정을 확인한 뒤 다시 시도해 주세요.")
            return
        display_revision = str(revision or "").strip()
        target = self._find_panel_message(session, int(panel_index))
        if target is None:
            return
        target.kind = "generation"
        target.text = f"{panel_index}컷을 다시 생성하고 있습니다…"
        target.metadata = {
            "phase": "panel_revision",
            "panel_index": int(panel_index),
            "current": max(0, int(panel_index) - 1),
            "revision": display_revision,
        }
        session.status = "generating"
        session.error_message = ""
        session.touch()
        self.session_manager.update(session)
        message_id = target.id
        self.window.begin_panel_regeneration(panel_index, display_revision, session)
        self.window.set_generation_busy(True)
        self.active_worker = PanelRegenerationWorker(service, comic, int(panel_index), display_revision)
        self.active_session_id = session.id
        self.active_message_id = message_id
        self._operation = "panel_regen"
        self._active_panel_index = int(panel_index)
        self._active_panel_revision = display_revision
        self._active_panel_message_id = message_id
        worker = self.active_worker
        worker.panel_started.connect(self._on_panel_regen_started)
        worker.panel_generated.connect(self._on_panel_regen_generated)
        worker.compose_started.connect(self._on_panel_regen_compose_started)
        worker.finished_comic.connect(self._on_panel_regen_finished)
        worker.failed.connect(self._on_panel_regen_failed)
        worker.cancelled.connect(self._on_panel_regen_cancelled)
        worker.finished.connect(self._release_worker)
        worker.start()

    def _find_panel_message(self, session, panel_index):
        for message in reversed(session.messages):
            if message.kind == "panel_result" and int(message.metadata.get("panel_index", 0) or 0) == int(panel_index):
                return message
        return None

    def _on_panel_regen_started(self, index):
        if not self.active_message_id:
            return
        session = self._target_session()
        if session is None:
            return
        self._update_active_generation_message(session, f"{index}컷 이미지를 다시 생성하는 중…", max(0, index - 1))
        self.window.update_generation(self.active_message_id, f"{index}컷 이미지를 다시 생성하는 중…", max(0, index - 1), 4)

    def _on_panel_regen_generated(self, index, path):
        if not self.active_message_id:
            return
        session = self._target_session()
        if session is None:
            return
        text = f"{index}컷 이미지 생성 완료 · 4컷 합성 준비 중…"
        self._update_active_generation_message(session, text, max(0, index - 1))
        self.window.update_generation(self.active_message_id, text, max(0, index - 1), 4)

    def _update_active_generation_message(self, session, text, current):
        item = self._message(session, self.active_message_id)
        if item is not None:
            item.text = text
            item.metadata["current"] = int(current)
            session.touch()
            self.session_manager.update(session)

    def _on_panel_regen_compose_started(self):
        session = self._target_session()
        if not session:
            return
        data = ChatMessageData(
            role="ai", kind="generation", text="4컷 최종 합성중…",
            metadata={"phase": "compose", "panel_index": 0, "current": 4},
        )
        session.add_message(data)
        self.session_manager.update(session)
        self.active_message_id = data.id
        self.window.show_generation_message(data)

    def _restore_committed_panel_message(self):
        if not self._active_panel_message_id or not self._active_panel_index:
            return
        session = self._target_session()
        if session is None:
            return
        item = self._message(session, self._active_panel_message_id)
        index = int(self._active_panel_index)
        path = session.panel_paths[index - 1] if 1 <= index <= len(session.panel_paths) else ""
        panels = (session.comic_data or {}).get("panels") or []
        dialogue = status = ""
        if 1 <= index <= len(panels):
            panel = panels[index - 1]
            dialogue = str(panel.get("dialogue") or "")
            status = str(panel.get("dialogue_status") or "")
            path = path or str(panel.get("image_path") or "")
        if item is not None:
            item.kind = "panel_result"
            item.text = self._panel_result_text(index, status)
            item.metadata = {"panel_index": index, "path": path, "dialogue": dialogue, "dialogue_status": status}
            session.touch()
            self.session_manager.update(session)
            self.window.restore_panel_result_message(session)

    def _on_panel_regen_finished(self, comic):
        session = self._target_session()
        message_id = self.active_message_id
        index = self._active_panel_index
        if session is not None and index:
            self._commit_panel_regeneration(session, message_id, index, comic)
            self.session_manager.update(session)
            self.window.finish_panel_regeneration(message_id, index, comic, session)
        self.active_message_id = None
        self.active_session_id = None
        self._operation = ""
        self._active_panel_index = None
        self._active_panel_revision = ""
        self._active_panel_message_id = None

    def _commit_panel_regeneration(self, session, message_id, panel_index, comic):
        # 합성용 generation 메시지는 제거하고, 원래 컷 메시지(재생성 대상)를 panel_result로 되돌린다.
        if message_id:
            session.messages = [m for m in session.messages if m.id != message_id]
        target = self._message(session, self._active_panel_message_id)
        session.panel_paths = [p.image_path for p in getattr(comic, "panels", []) if getattr(p, "image_path", "")]
        session.result_path = str(getattr(comic, "output_path", "") or session.result_path)
        session.master_seed = int(getattr(comic, "master_seed", session.master_seed) or 0)
        session.character_prompt = str(getattr(comic, "character_prompt", session.character_prompt) or "")
        session.style_prompt = str(getattr(comic, "style_prompt", session.style_prompt) or "")
        session.generation_config = dict(getattr(comic, "generation_config", session.generation_config) or {})
        session.comic_data = comic.to_dict() if hasattr(comic, "to_dict") else dict(session.comic_data)
        idx = int(panel_index)
        panels = getattr(comic, "panels", [])
        new_path = dialogue = status = ""
        if 1 <= idx <= len(panels):
            panel = panels[idx - 1]
            new_path = str(getattr(panel, "image_path", "") or "")
            dialogue = str(getattr(panel, "dialogue", "") or "")
            status = str(getattr(panel, "dialogue_status", "") or "")
        if target is not None:
            target.kind = "panel_result"
            target.text = self._panel_result_text(idx, status)
            target.metadata = {"panel_index": idx, "path": new_path, "dialogue": dialogue, "dialogue_status": status}
        else:
            session.add_message(ChatMessageData(
                role="ai", kind="panel_result",
                text=self._panel_result_text(idx, status),
                metadata={"panel_index": idx, "path": new_path, "dialogue": dialogue, "dialogue_status": status},
            ))
        session.status = "completed"
        session.error_message = ""
        self._upsert_result_message(session, comic)
        session.touch()

    @staticmethod
    def _upsert_result_message(session, comic):
        result = next((m for m in reversed(session.messages) if m.kind == "result"), None)
        if result is None:
            session.add_message(ChatMessageData(
                role="ai", kind="result", text="완성",
                metadata={"result_path": getattr(comic, "output_path", "") or ""},
            ))
        else:
            result.text = "완성"
            result.metadata["result_path"] = getattr(comic, "output_path", "") or session.result_path

    def _on_panel_regen_failed(self, message):
        message_id = self.active_message_id
        session = self._target_session()
        if session is not None:
            item = self._message(session, message_id)
            if item is not None:
                item.text = str(message)
                item.metadata["failed"] = True
            session.status = "failed"
            session.error_message = str(message)
            session.touch()
            self.session_manager.update(session)
            self.window.fail_generation(message_id, str(message), session)
            self._restore_committed_panel_message()
        self.active_message_id = None
        self.active_session_id = None
        self._operation = ""
        self._active_panel_index = None
        self._active_panel_revision = ""
        self._active_panel_message_id = None

    def _on_panel_regen_cancelled(self):
        message_id = self.active_message_id
        session = self._target_session()
        if session is not None:
            item = self._message(session, message_id)
            if item is not None:
                item.text = "생성이 취소되었습니다."
                item.metadata["cancelled"] = True
            session.status = "cancelled"
            session.touch()
            self.session_manager.update(session)
            self.window.cancel_generation_ui(message_id, session)
            self._restore_committed_panel_message()
        self.active_message_id = None
        self.active_session_id = None
        self._operation = ""
        self._active_panel_index = None
        self._active_panel_revision = ""
        self._active_panel_message_id = None

    def cancel_generation(self):
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()

    @staticmethod
    def _style_from_labels(mood, art_style):
        return ", ".join(p for p in (ART_STYLE_PRESETS.get(art_style, ""), STYLE_PRESETS.get(mood, "")) if p)

    def regenerate(self):
        session = self.get_session()
        if not session or session.status == "generating":
            return
        idea = self.last_idea or session.idea
        if not idea:
            return
        if not self.last_idea:
            self.last_mood = session.mood
            self.last_art_style = session.art_style
        style_prompt = str(session.style_prompt or "") or self.last_style_prompt or self._style_from_labels(session.mood, session.art_style)
        character_prompt = str(session.character_prompt or "")
        service = None
        if session.generation_config:
            try:
                service = self._service_for_session(session)
            except Exception:
                logger.exception("저장된 생성 설정을 다시 준비하지 못했습니다.")
        self._is_revising = False
        self.start_generation(
            idea, style_prompt, session.mood or self.last_mood, session.art_style or self.last_art_style,
            add_user=False, update_title=False, service=service, character_prompt=character_prompt or None,
        )

    def revise(self, revision, style_prompt=None, mood=None, art_style=None):
        revision = revision.strip()
        session = self.get_session()
        if not revision or not session or session.status == "generating":
            return
        base_idea = self.last_idea or session.idea
        if not base_idea:
            return
        mood = mood or session.mood or self.last_mood
        art_style = art_style or session.art_style or self.last_art_style
        style_prompt = style_prompt if style_prompt is not None else self._style_from_labels(mood, art_style)
        revised_idea = f"{base_idea}\n사용자 수정 요청: {revision}"
        self._is_revising = True
        self.start_generation(revised_idea, style_prompt, mood, art_style, display_text=revision, update_title=False, add_user=True)

    @staticmethod
    def _story_summary(comic, session):
        character = getattr(comic, "character", None)
        return {
            "title": str(getattr(comic, "title", "") or "4컷 스토리 계획"),
            "mood": str(getattr(session, "mood", "") or ""),
            "art_style": str(getattr(session, "art_style", "") or ""),
            "style": str(getattr(comic, "style", "") or ""),
            "character": {
                "name": str(getattr(character, "name", "") or ""),
                "appearance": str(getattr(character, "appearance", "") or ""),
                "personality": str(getattr(character, "personality", "") or ""),
            },
            "panels": [
                {
                    "scene": str(getattr(panel, "scene", "") or ""),
                    "dialogue": str(getattr(panel, "dialogue", "") or ""),
                    "speaker": str(getattr(panel, "speaker", "") or ""),
                }
                for panel in getattr(comic, "panels", [])
            ],
        }

    @staticmethod
    def _panel_result_text(index, status):
        status = str(status or "")
        if status == "composited":
            return f"{index}컷 이미지와 대사 합성이 완료되었습니다."
        if status == "failed":
            return f"{index}컷 이미지가 완료되었지만 대사 합성에 실패했습니다. 최종 합성에서 대체 처리됩니다."
        if status == "skipped":
            return f"{index}컷 이미지가 완료되었습니다. (2단계 합성 미설정 — 최종 합성에서 대사를 그립니다)"
        if status == "fallback":
            return f"{index}컷 이미지와 대사(대체 합성)가 완료되었습니다."
        if status == "none":
            return f"{index}컷 이미지가 완료되었습니다."
        return f"{index}컷 이미지와 대사 합성이 완료되었습니다."

    def _on_save_error(self, message):
        self.window.warning_message("저장 실패", message)
