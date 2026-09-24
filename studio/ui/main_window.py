from pathlib import Path
import shutil

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from studio.settings.settings_window import SettingsWindow
from studio.models.chat import ChatMessageData, ChatSession
from studio.services.session_manager import SessionManager
from studio.ui import theme
from studio.ui.chat_view_manager import ChatViewManager
from studio.ui.composer import Composer
from studio.ui.sidebar import Sidebar
from studio.ui.styles import MAIN_WINDOW_QSS_TEMPLATE
from studio.workers.server_status_worker import ServerStatusWorker
from studio.version import APP_NAME, APP_VERSION



class MainWindow(QMainWindow):
    settingsApplied = Signal()
    generationRequested = Signal(str, str, str, str)  # idea, style_prompt, mood label, art label
    cancelRequested = Signal()
    regenerateRequested = Signal()
    revisionRequested = Signal(str)
    panelRegenerateRequested = Signal(int)
    panelRevisionRequested = Signal(int, str)

    # $TOKEN 형태의 QSS 템플릿. 실제 정의는 ui.main.styles 모듈로 분리했다.
    # 하위 호환을 위해 클래스 속성으로 유지한다.
    QSS_TEMPLATE = MAIN_WINDOW_QSS_TEMPLATE

    def __init__(self, settings_manager, lm_factory, comfy_factory, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.lm_factory = lm_factory
        self.comfy_factory = comfy_factory
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1200, 820)
        self.setMinimumSize(960, 700)
        self.setStyleSheet(theme.render(self.QSS_TEMPLATE))

        self.session_manager = SessionManager(settings_manager)
        self.current_session = None
        self._server_worker = None
        self._server_state = (False, False)
        self._generating_session_id = None

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        root_layout.addWidget(self._build_header())
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.sidebar = Sidebar()
        self.sidebar.setMinimumWidth(200)
        self.sidebar.setMaximumWidth(360)
        splitter.addWidget(self.sidebar)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.chat_view = ChatViewManager(
            on_save_comic=self.save_comic,
            on_cancel=self._on_cancel_requested,
            on_regenerate=self.regenerateRequested.emit,
            on_panel_regenerate=self.panelRegenerateRequested.emit,
            on_panel_revision=self.panelRevisionRequested.emit,
            parent=main,
        )
        self.chat = self.chat_view.chat
        self.empty = self.chat_view.empty
        self.composer = Composer(settings_manager)
        main_layout.addWidget(self.empty, 1)
        main_layout.addWidget(self.chat, 1)
        main_layout.addWidget(self.composer, 0)
        splitter.addWidget(main)
        splitter.setSizes([260, 940])
        root_layout.addWidget(splitter, 1)

        self.form = type("FormProxy", (), {})()
        self.form.settingsButton = None
        self.form.saveStatusLabel = self.status_label

        self.sidebar.newChatRequested.connect(self.new_chat)
        self.sidebar.sessionSelected.connect(self.open_session)
        self.sidebar.sessionDeleteRequested.connect(self.delete_session)
        self.sidebar.sessionRenamed.connect(self.rename_session)
        self.sidebar.settingsRequested.connect(self.open_settings)
        self.composer.submitted.connect(self.generationRequested.emit)

        # 메인 입력창은 공통 Composer를 사용하므로 하위 화면들의 중복 입력창을 만들지 않는다.
        self.statusBar().showMessage("새 채팅을 시작해 보세요.")
        self._refresh_sidebar()
        if not self.session_manager.sessions:
            self.new_chat(auto=True)
        else:
            self.open_session(self.session_manager.sessions[0].id)
        self.refresh_server_status()

    def closeEvent(self, event):
        # 종료 시 대기 중인 디바운스 세션 저장을 즉시 커밋한다.
        try:
            self.session_manager.flush()
        except Exception:
            pass
        super().closeEvent(event)

    def _build_header(self):
        header = QFrame()
        header.setObjectName("headerFrame")
        header.setFixedHeight(64)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 20, 0)
        layout.setSpacing(12)
        logo = QLabel(f"✦ 4cut Studio <span style='font-size:12px; font-weight:700; color:{theme.TEXT_FAINT}'>{APP_VERSION}</span>")
        logo.setObjectName("logoLabel")
        layout.addWidget(logo)
        self.status_label = QLabel("● AI 서버 확인 중...")
        self.status_label.setObjectName("saveStatusLabel")
        self._set_status_label("● AI 서버 확인 중...", "checking")
        layout.addWidget(self.status_label)
        layout.addStretch(1)
        return header

    def _set_status_label(self, text, state="connected"):
        self.status_label.setText(text)
        self.status_label.setProperty("state", state)
        style = self.status_label.style()
        style.unpolish(self.status_label)
        style.polish(self.status_label)
        self.status_label.update()

    def _refresh_sidebar(self):
        selected = self.current_session.id if self.current_session else None
        self.sidebar.set_sessions(self.session_manager.sessions, selected)

    def new_chat(self, auto=False):
        if self.current_session and not auto and not self.current_session.messages:
            self.open_session(self.current_session.id)
            return
        session = ChatSession()
        session.add_message(ChatMessageData(role="ai", kind="text", text="안녕하세요! 아이디어를 입력하면 스토리부터 4컷 완성까지 도와드릴게요."))
        self.session_manager.add(session)
        self.current_session = session
        self._refresh_sidebar()
        self._render_session(session)
        self.composer.idea.clear()
        self.composer.load_session_options(session)
        self.composer.set_busy(False)
        self.statusBar().showMessage("새 대화가 시작되었습니다.")

    def open_session(self, session_id):
        session = self.session_manager.get(session_id)
        if not session:
            return
        self.current_session = session
        self._render_session(session)
        self.composer.load_session_options(session)
        self.composer.idea.clear()
        # 생성 중인 세션은 입력을 잠그고, 다른 세션으로 이동해도 전역 생성 중 상태를 유지한다.
        self.composer.set_busy(self._generating_session_id is not None)
        self.statusBar().showMessage(
            "현재 대화에서 생성 중입니다." if session.status == "generating" else "대화를 열었습니다.",
            2000,
        )

    def delete_session(self, session_id):
        session = self.session_manager.get(session_id)
        if not session:
            return
        if session.status == "generating":
            QMessageBox.information(self, "삭제할 수 없음", "생성 중인 대화는 생성이 끝나거나 취소될 때까지 삭제할 수 없습니다.")
            self._refresh_sidebar()
            return
        answer = QMessageBox.question(
            self,
            "대화 삭제",
            f"'{session.title}' 대화를 삭제할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if not self.session_manager.remove(session_id):
            return
        if self.current_session and self.current_session.id == session_id:
            self.current_session = None
            if self.session_manager.sessions:
                self.open_session(self.session_manager.sessions[0].id)
            else:
                self.new_chat()
            # open_session()은 사이드바를 다시 그리지 않으므로 삭제가 목록에 즉시 반영되도록 갱신한다.
            self._refresh_sidebar()
        else:
            self._refresh_sidebar()

    def rename_session(self, session_id, title):
        session = self.session_manager.get(session_id)
        if not session or session.status == "generating":
            return
        clean = " ".join(title.replace("⟳", "").replace("!", "").replace("·", "").split())[:40]
        if clean:
            session.title = clean
            session.touch()
            self.session_manager.update(session)
            if self.current_session and self.current_session.id == session.id:
                self.statusBar().showMessage(f"대화 이름을 '{clean}'으로 변경했습니다.", 2500)
            self._refresh_sidebar()

    def _render_session(self, session):
        self.chat_view.set_current_session(session)
        self.chat_view.render_session(session)
        if session.status == "generating":
            self.composer.set_busy(True)
    def ensure_user_message(self, text, mood, art_style, idea_value=None, update_title=True):
        session = self.current_session
        if session is None:
            self.new_chat()
            session = self.current_session
        message = ChatMessageData(role="user", kind="text", text=text, mood=mood, art_style=art_style)
        session.add_message(message)
        session.idea = idea_value if idea_value is not None else text
        session.mood = mood
        session.art_style = art_style
        if update_title:
            session.set_title_from_idea(text)
        self.session_manager.update(session)
        self.chat_view.append_user_message(text, mood, art_style)
        return session

    def add_ai_text(self, text):
        self.chat_view.add_ai_text(text)

    def _on_cancel_requested(self):
        self.cancelRequested.emit()

    def add_generation_message(self, session, initial="생성을 준비하는 중…", phase="story", panel_index=0):
        message_id = self.chat_view.add_generation_message(session, initial, phase, panel_index)
        self.session_manager.update(session)
        self.composer.set_busy(True)
        return message_id


    @staticmethod
    def _story_summary(comic, session):
        return ChatViewManager._story_summary(comic, session)

    def complete_story_plan(self, message_id, comic, session_id=None):
        """진행용 스토리 카드를 영구적인 요약 카드로 전환한다."""
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session or not message_id:
            return
        item = next((message for message in session.messages if message.id == message_id), None)
        if item is None:
            return
        self.chat_view.complete_story_plan(message_id, comic, session)
        self.session_manager.update(session)

    @staticmethod
    def _panel_result_text(index, status):
        return ChatViewManager._panel_result_text(index, status)

    def restore_panel_result_message(self, message_id, panel_index, session_id=None):
        """재생성 실패/취소 시 덮어쓴 컷 메시지를 마지막 커밋본 결과로 복원한다.

        panel_paths/comic_data는 실패·취소 시점까지 보존되므로 그 값으로
        재구성하며, 세션 상태(실패/취소)는 호출한 fail/cancel 쪽이 관리한다.
        """
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session:
            return
        item = next((m for m in session.messages if m.id == message_id), None)
        if item is None:
            return
        self.chat_view.restore_panel_result_message(message_id, panel_index, session)
        self.session_manager.update(session)

    def begin_panel_generation(self, message_id, index, message):
        self.chat_view.begin_panel_generation(message_id, message, index)
        session = self.session_manager.get(self._generating_session_id) if self._generating_session_id else self.current_session
        if session:
            item = next((m for m in session.messages if m.id == message_id), None)
            if item:
                item.text = message
                item.metadata.update({"phase": "panel", "panel_index": index, "current": max(0, index - 1)})
                session.touch()
                self.session_manager.update(session)

    def begin_final_composition(self, message_id, message):
        self.chat_view.begin_final_composition(message_id, message)
        session = self.session_manager.get(self._generating_session_id) if self._generating_session_id else self.current_session
        if session:
            item = next((m for m in session.messages if m.id == message_id), None)
            if item:
                item.text = message
                item.metadata.update({"phase": "compose", "current": 4})
                session.touch()
                self.session_manager.update(session)

    def add_panel_generation_message(self, session, index):
        return self.add_generation_message(
            session,
            initial=f"{index}컷 이미지 생성중…",
            phase="panel",
            panel_index=index,
        )

    def update_generation(self, message_id, message, current, total, session_id=None):
        self.chat_view.update_generation(message_id, message, current, total)
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if session:
            item = next((m for m in session.messages if m.id == message_id), None)
            if item:
                item.text = message
                item.metadata["current"] = current
                session.touch()
                self.session_manager.update(session)

    def complete_panel_generation(self, message_id, index, path, dialogue="", dialogue_status="", session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if session:
            self.chat_view.complete_panel_generation(
                message_id, index, path, dialogue=dialogue, dialogue_status=dialogue_status, session=session
            )
            self.session_manager.update(session)

    def begin_panel_regeneration(self, panel_index, revision="", session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session:
            return None
        message_id = self.chat_view.begin_panel_regeneration(panel_index, revision, session=session)
        if message_id is None:
            return None
        self.session_manager.update(session)
        self._generating_session_id = session.id
        self.composer.set_busy(True)
        self._set_status_label("● AI 작업 중", "busy")
        self._refresh_sidebar()
        return message_id

    def add_panel_compose_message(self, session):
        return self.add_generation_message(
            session,
            initial="4컷 최종 합성중…",
            phase="compose",
        )

    def finish_panel_regeneration(self, message_id, panel_index, comic, session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session:
            return
        self.chat_view.finish_panel_regeneration(message_id, panel_index, comic, session=session)
        self.session_manager.update(session)
        self._generating_session_id = None
        self.composer.set_busy(False)
        self._refresh_sidebar()
        self._set_status_label("● 생성 완료", "done")
        self.statusBar().showMessage(f"{panel_index}컷 재생성과 최종 합성이 완료되었습니다.", 4000)

    def finish_generation(self, message_id, comic, session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session:
            return
        self.chat_view.finish_generation(message_id, comic, session=session)
        self.session_manager.update(session)
        self.composer.set_busy(False)
        self._generating_session_id = None
        self._refresh_sidebar()
        self._set_status_label("● 생성 완료", "done")
        self.statusBar().showMessage("4컷 만화가 완성되었습니다.", 4000)

    def fail_generation(self, message_id, message, session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session:
            return
        self.chat_view.fail_generation(message_id, message, session=session)
        self.session_manager.update(session)
        self.composer.set_busy(False)
        self._generating_session_id = None
        self._set_status_label("● 생성 오류", "error")
        self._refresh_sidebar()

    def cancel_generation_ui(self, message_id, session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if not session:
            return
        self.chat_view.cancel_generation_ui(message_id, session=session)
        self.session_manager.update(session)
        self.composer.set_busy(False)
        self._generating_session_id = None
        self._set_status_label("● AI 서버 연결됨" if all(self._server_state) else "● AI 서버 확인 필요", "connected" if all(self._server_state) else "error")
        self._refresh_sidebar()

    def mark_generating(self, session_id=None):
        session = self.session_manager.get(session_id) if session_id else self.current_session
        if session:
            session.status = "generating"
            session.error_message = ""
            session.touch()
            self.session_manager.update(session)
            self._generating_session_id = session.id
        self._set_status_label("● AI 작업 중", "busy")
        self.composer.set_busy(True)
        self._refresh_sidebar()

    def save_comic(self, comic):
        path = getattr(comic, "output_path", "")
        if not path or not Path(path).exists():
            QMessageBox.warning(self, "저장할 이미지 없음", "완성된 4컷 이미지를 찾을 수 없습니다.")
            return
        target, _ = QFileDialog.getSaveFileName(self, "4컷 만화 저장", "4cut.png", "PNG (*.png)")
        if target:
            try:
                shutil.copy2(path, target)
                self.statusBar().showMessage(f"이미지를 저장했습니다: {target}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "저장 실패", str(e))

    def refresh_server_status(self):
        if self._server_worker and self._server_worker.isRunning():
            return
        self._set_status_label("● AI 서버 확인 중...", "checking")
        self._server_worker = ServerStatusWorker(self.lm_factory, self.comfy_factory, self.settings_manager, self)
        self._server_worker.checked.connect(self._on_server_status)
        self._server_worker.finished.connect(self._release_server_worker)
        self._server_worker.start()

    def _release_server_worker(self):
        self._server_worker = None

    def _on_server_status(self, lm_ok, comfy_ok, errors):
        self._server_state = (lm_ok, comfy_ok)
        if self._generating_session_id is not None:
            self._set_status_label("● AI 작업 중", "busy")
        elif lm_ok and comfy_ok:
            if self.current_session and self.current_session.status == "completed":
                self._set_status_label("● 생성 완료", "done")
            else:
                self._set_status_label("● AI 서버 연결됨", "connected")
        elif lm_ok or comfy_ok:
            self._set_status_label("● 일부 AI 서버 연결됨", "connected")
        else:
            self._set_status_label("● AI 서버 미연결", "error")
        if errors and self.current_session:
            self.statusBar().showMessage("AI 서버 연결을 확인하세요. 설정에서 주소와 연결 상태를 확인할 수 있습니다.", 6000)

    def reload_theme(self):
        theme.load_fonts()
        self.setStyleSheet(theme.render(self.QSS_TEMPLATE))

    def open_settings(self):
        if getattr(self, "settings_dialog", None) is not None:
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
            return
        try:
            self.settings_dialog = SettingsWindow(self.settings_manager, self.lm_factory, self.comfy_factory, self)
            result = self.settings_dialog.form.exec()
            if result:
                self.settingsApplied.emit()
                self.reload_theme()
                self._set_status_label("● 설정 저장됨 · 서버 확인 중...", "checking")
                self.statusBar().showMessage("설정이 저장되었습니다. 서버 연결을 다시 확인합니다.", 4000)
                self.refresh_server_status()
        except Exception as e:
            QMessageBox.critical(self, "설정창 오류", f"설정창을 열 수 없습니다.\n\n{e}")
        finally:
            self.settings_dialog = None
