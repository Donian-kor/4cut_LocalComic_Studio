import re
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox

from core.workers.comic_worker import ComicWorker
from core.workers.panel_regeneration_worker import PanelRegenerationWorker
from core.models.comic import Comic
from ui.idea.idea_section import IdeaSection


class MainController(QObject):
    """채팅 UI와 기존 ComicWorker 파이프라인을 연결한다.

    생성 UI는 한 컷씩 순차적으로 채팅에 추가한다.
    - 첫 progress: 스토리 구성
    - N컷 생성 시작: N컷 생성 카드 1개 표시
    - panel_completed: 해당 생성 카드를 제거하고 N컷 결과 카드 표시
    - 다음 progress: 다음 컷 생성 카드 추가
    - 마지막: 최종 4컷 합성 카드 표시 후 결과 카드 추가
    """

    def __init__(self, main_window, service_factory):
        super().__init__(main_window)
        self.window = main_window
        self.service_factory = service_factory
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

        main_window.generationRequested.connect(self.handle_composer_message)
        main_window.cancelRequested.connect(self.cancel_generation)
        main_window.regenerateRequested.connect(self.regenerate)
        main_window.panelRegenerateRequested.connect(self.regenerate_panel)
        main_window.panelRevisionRequested.connect(self.revise_panel)
        main_window.settingsApplied.connect(self.settings_changed)

    def settings_changed(self):
        if self.active_worker and self.active_worker.isRunning():
            return
        try:
            self.service = self.service_factory()
        except Exception as e:
            self.service = None
            QMessageBox.warning(self.window, "설정 확인 필요", f"AI 생성 설정을 준비하지 못했습니다.\n\n{e}")

    def _server_ready(self):
        return all(getattr(self.window, "_server_state", (False, False)))

    def handle_composer_message(self, text, style_prompt, mood, art_style):
        if self.active_worker and self.active_worker.isRunning():
            self.window.statusBar().showMessage("현재 다른 대화에서 생성 중입니다. 생성이 끝난 뒤 새 요청을 보내 주세요.", 3000)
            return
        text = text.strip()
        if not text:
            return

        session = self.window.current_session
        has_result = bool(session and session.result_path and session.status in {"completed", "failed", "cancelled"})
        if has_result:
            self.revise(text, style_prompt=style_prompt, mood=mood, art_style=art_style)
        else:
            self.start_generation(text, style_prompt, mood, art_style)

    def start_generation(self, idea, style_prompt, mood, art_style, display_text=None, update_title=True, add_user=True):
        if self.active_worker and self.active_worker.isRunning():
            return
        idea = idea.strip()
        if not idea:
            return

        if add_user:
            session = self.window.ensure_user_message(
                display_text if display_text is not None else idea,
                mood,
                art_style,
                idea_value=idea,
                update_title=update_title,
            )
        else:
            session = self.window.current_session
            if session is None:
                session = self.window.ensure_user_message(idea, mood, art_style)

        if not self._server_ready():
            self.window.add_ai_text("LM Studio와 ComfyUI가 모두 연결되어야 4컷 만화를 만들 수 있어요. 설정에서 연결을 확인해 주세요.")
            self.window.refresh_server_status()
            return

        try:
            self.service = self.service_factory()
        except Exception as e:
            self.window.add_ai_text(f"생성 설정을 준비하지 못했습니다.\n\n{e}")
            return

        self.last_idea = idea
        self.last_style_prompt = style_prompt
        self.last_mood = mood
        self.last_art_style = art_style
        self.active_session_id = session.id
        self.window.mark_generating(session.id)
        self.active_message_id = self.window.add_generation_message(session, initial="스토리 구성 중…", phase="story")

        worker = ComicWorker(self.service, idea, style_prompt)
        self.active_worker = worker
        worker.progress.connect(self._on_progress)
        worker.planned.connect(self._on_planned)
        worker.panel_completed.connect(self._on_panel_completed)
        worker.finished_comic.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.cancelled.connect(self._on_cancelled)
        worker.finished.connect(self._release_worker)
        worker.start()

    def _on_planned(self, comic):
        session = self._target_session()
        if session is None or comic is None:
            return
        session.master_seed = int(getattr(comic, "master_seed", 0) or 0)
        session.character_prompt = str(getattr(comic, "character_prompt", "") or "")
        session.style_prompt = str(getattr(comic, "style_prompt", "") or "")
        session.generation_config = dict(getattr(comic, "generation_config", {}) or {})
        session.touch()
        self.window.session_manager.update(session)

    @staticmethod
    def _panel_index_from_progress(message):
        match = re.search(r"([1-4])컷\s+이미지\s+생성\s+중", str(message))
        return int(match.group(1)) if match else None

    def _target_session(self):
        if not self.active_session_id:
            return None
        return self.window.session_manager.get(self.active_session_id)

    def _on_progress(self, message, current, total):
        panel_index = self._panel_index_from_progress(message)
        if panel_index:
            session = self._target_session()
            if session is None:
                return
            if self.active_message_id is None:
                self.active_message_id = self.window.add_generation_message(
                    session,
                    initial=message,
                    phase="panel",
                    panel_index=panel_index,
                )
            else:
                self.window.begin_panel_generation(self.active_message_id, panel_index, message)
            return

        if "4컷 합성 중" in str(message):
            session = self._target_session()
            if session is None:
                return
            if self.active_message_id is None:
                self.active_message_id = self.window.add_generation_message(
                    session,
                    initial=message,
                    phase="compose",
                )
            else:
                self.window.begin_final_composition(self.active_message_id, message)
            return

        if self.active_message_id:
            self.window.update_generation(self.active_message_id, message, current, total, self.active_session_id)

    def _on_panel_completed(self, index, path):
        message_id = self.active_message_id
        if not message_id:
            return

        dialogue = ""
        if self.active_worker is not None:
            comic = getattr(self.active_worker, "comic", None)
            panels = getattr(comic, "panels", []) if comic else []
            if 1 <= index <= len(panels):
                dialogue = str(getattr(panels[index - 1], "dialogue", "") or "")

        self.window.complete_panel_generation(
            message_id,
            index,
            path,
            dialogue=dialogue,
            session_id=self.active_session_id,
        )
        self.active_message_id = None

    def _on_finished(self, comic):
        message_id = self.active_message_id
        self.active_message_id = None
        self._is_revising = False
        self.window.finish_generation(message_id, comic, session_id=self.active_session_id)
        self.last_idea = comic.idea or self.last_idea
        self.active_session_id = None

    def _on_failed(self, message):
        message_id = self.active_message_id
        self.active_message_id = None
        was_revising = self._is_revising
        self._is_revising = False
        self.window.fail_generation(message_id, message, session_id=self.active_session_id)
        if was_revising:
            self.window.add_ai_text(f"수정 요청을 반영하지 못했습니다.\n{message}")
        self.active_session_id = None

    def _on_cancelled(self):
        message_id = self.active_message_id
        self.active_message_id = None
        self._is_revising = False
        self.window.cancel_generation_ui(message_id, session_id=self.active_session_id)
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
            return None

    def _service_for_session(self, session):
        model_id = str((session.generation_config or {}).get("id", "") or "").strip()
        try:
            return self.service_factory(model_id or None)
        except TypeError:
            # 구버전 factory 호환
            return self.service_factory()

    def regenerate_panel(self, panel_index):
        self._start_panel_regeneration(panel_index, "")

    def revise_panel(self, panel_index, revision):
        self._start_panel_regeneration(panel_index, revision or "")

    def _start_panel_regeneration(self, panel_index, revision):
        if self.active_worker and self.active_worker.isRunning():
            return
        session = self.window.current_session
        if not session or session.status == "generating":
            return
        comic = self._comic_from_session(session)
        if comic is None or not (1 <= int(panel_index) <= len(comic.panels)):
            QMessageBox.warning(self.window, "재생성할 수 없음", "저장된 컷 생성 정보가 없어 해당 컷을 다시 만들 수 없습니다.")
            return
        try:
            service = self._service_for_session(session)
            if session.result_path:
                service.set_run_folder(Path(session.result_path).parent)
        except Exception as e:
            QMessageBox.warning(self.window, "생성 설정 확인 필요", f"기존 생성 설정을 준비하지 못했습니다.\n\n{e}")
            return

        display_revision = str(revision or "").strip()
        message_id = self.window.begin_panel_regeneration(
            int(panel_index), display_revision, session_id=session.id
        )
        if not message_id:
            return
        worker = PanelRegenerationWorker(service, comic, int(panel_index), display_revision)
        self.active_worker = worker
        self.active_session_id = session.id
        self.active_message_id = message_id
        self._operation = "panel_regen"
        self._active_panel_index = int(panel_index)
        self._active_panel_revision = display_revision
        worker.panel_completed.connect(self._on_panel_regen_completed)
        worker.compose_started.connect(self._on_panel_regen_compose_started)
        worker.finished_comic.connect(self._on_panel_regen_finished)
        worker.failed.connect(self._on_panel_regen_failed)
        worker.cancelled.connect(self._on_panel_regen_cancelled)
        worker.finished.connect(self._release_worker)
        worker.start()

    def _on_panel_regen_completed(self, index, path):
        # UI 메시지를 먼저 완성 카드로 바꾼 뒤 최종 합성 카드를 별도로 추가한다.
        session = self._target_session()
        if not session:
            return
        comic = getattr(self.active_worker, "comic", None)
        dialogue = ""
        if comic and 1 <= index <= len(comic.panels):
            dialogue = comic.panels[index - 1].dialogue
        self.window.complete_panel_generation(
            self.active_message_id, index, path, dialogue=dialogue, session_id=self.active_session_id
        )

    def _on_panel_regen_compose_started(self):
        session = self._target_session()
        if not session:
            return
        # 새 합성 카드 ID로 교체한다. 기존 컷 결과는 그대로 채팅에 남는다.
        self.active_message_id = self.window.add_panel_compose_message(session)

    def _on_panel_regen_finished(self, comic):
        message_id = self.active_message_id
        self._is_revising = False
        # compose 카드라면 finish_panel_regeneration이 카드 제거 대신 최종 결과를 갱신한다.
        self.window.finish_panel_regeneration(
            message_id, self._active_panel_index, comic, session_id=self.active_session_id
        )
        session = self._target_session()
        if session:
            session.comic = comic
        self.active_message_id = None
        self.active_session_id = None
        self._operation = ""
        self._active_panel_index = None
        self._active_panel_revision = ""

    def _on_panel_regen_failed(self, message):
        message_id = self.active_message_id
        self.window.fail_generation(message_id, message, session_id=self.active_session_id)
        self.active_message_id = None
        self.active_session_id = None
        self._operation = ""
        self._active_panel_index = None
        self._active_panel_revision = ""

    def _on_panel_regen_cancelled(self):
        message_id = self.active_message_id
        self.window.cancel_generation_ui(message_id, session_id=self.active_session_id)
        self.active_message_id = None
        self.active_session_id = None
        self._operation = ""
        self._active_panel_index = None
        self._active_panel_revision = ""

    def cancel_generation(self):
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()

    def _style_from_labels(self, mood, art_style):
        return ", ".join(
            [
                p
                for p in (
                    IdeaSection.ART_STYLE_PRESETS.get(art_style, ""),
                    IdeaSection.STYLE_PRESETS.get(mood, ""),
                )
                if p
            ]
        )

    def regenerate(self):
        session = self.window.current_session
        if not session or session.status == "generating":
            return
        if not self.last_idea and session:
            self.last_idea = session.idea
            self.last_mood = session.mood
            self.last_art_style = session.art_style
            self.last_style_prompt = self._style_from_labels(self.last_mood, self.last_art_style)
        if self.last_idea:
            self._is_revising = False
            self.start_generation(
                self.last_idea,
                self.last_style_prompt,
                self.last_mood,
                self.last_art_style,
                add_user=False,
                update_title=False,
            )

    def revise(self, revision, style_prompt=None, mood=None, art_style=None):
        revision = revision.strip()
        session = self.window.current_session
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
        self.start_generation(
            revised_idea,
            style_prompt,
            mood,
            art_style,
            display_text=revision,
            update_title=False,
            add_user=True,
        )
