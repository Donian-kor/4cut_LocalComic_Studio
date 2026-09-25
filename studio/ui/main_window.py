from pathlib import Path
import logging
import shutil

from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QSplitter, QWidget

from studio.settings.settings_window import SettingsWindow
from studio.ui import theme
from studio.ui.chat_view_manager import ChatViewManager
from studio.ui.composer import Composer
from studio.ui.sidebar import Sidebar
from studio.ui.styles import MAIN_WINDOW_QSS_TEMPLATE
from studio.workers.server_status_worker import ServerStatusWorker
from studio.version import APP_NAME, APP_VERSION

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    settingsApplied = Signal()
    generationRequested = Signal(str, str, str, str)
    cancelRequested = Signal()
    regenerateRequested = Signal()
    revisionRequested = Signal(str)
    panelRegenerateRequested = Signal(int)
    panelRevisionRequested = Signal(int, str)
    QSS_TEMPLATE = MAIN_WINDOW_QSS_TEMPLATE

    def __init__(self, settings_manager, lm_factory, comfy_factory, session_manager=None, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.lm_factory = lm_factory
        self.comfy_factory = comfy_factory
        self.session_manager = session_manager
        self.controller = None
        self.current_session = None
        self._server_worker = None
        self._server_state = (False, False)
        self._generating_session_id = None
        self.settings_dialog = None
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1200, 820)
        self.setMinimumSize(960, 700)
        self.setStyleSheet(theme.render(self.QSS_TEMPLATE))

        loader = QUiLoader()
        ui_path = Path(__file__).with_name("main_window.ui")
        self.ui = loader.load(str(ui_path), self)
        if self.ui is None:
            raise RuntimeError(f"UI 파일 로드 실패: {ui_path}")
        self.setCentralWidget(self.ui)

        self.sidebar_host = self.ui.findChild(QWidget, "sidebarHost")
        self.chat_host = self.ui.findChild(QWidget, "chatHost")
        self.empty_host = self.ui.findChild(QWidget, "emptyHost")
        self.composer_host = self.ui.findChild(QWidget, "composerHost")

        # host 레이아웃에 명시적으로 넣어야 Host가 비어 있어도 위젯이 배치된다.
        # (parent만 지정하면 레이아웃이 위젯을 잡지 못해 0px로 접혀 안 보인다.)
        self.sidebar = Sidebar()
        self.sidebar_host.layout().addWidget(self.sidebar)
        self.composer = Composer()
        self.composer_host.layout().addWidget(self.composer)
        # 상태 라벨은 composer.ui의 전송버튼 좌측에 산다(헤더 제거로 이동).
        self.status_label = self.composer.status_label
        self._set_status_label("● AI 서버 확인 중...", "checking")
        self.chat_view = ChatViewManager(
            on_save_comic=self.save_comic,
            on_cancel=self._on_cancel_requested,
            on_regenerate=self.regenerateRequested.emit,
            on_panel_regenerate=self.panelRegenerateRequested.emit,
            on_panel_revision=self.panelRevisionRequested.emit,
            chat_parent=self.chat_host,
            empty_parent=self.empty_host,
        )
        self.chat = self.chat_view.chat
        self.empty = self.chat_view.empty

        main_splitter = self.ui.findChild(QSplitter, "mainSplitter")
        if main_splitter is not None:
            main_splitter.setStretchFactor(0, 0)
            main_splitter.setStretchFactor(1, 1)
            main_splitter.setSizes([260, 940])
        self.sidebar.setMinimumWidth(220)
        main_layout = self.composer_host.parentWidget().layout()
        if main_layout is not None:
            main_layout.setStretch(main_layout.indexOf(self.empty_host), 1)
            main_layout.setStretch(main_layout.indexOf(self.chat_host), 1)
            main_layout.setStretch(main_layout.indexOf(self.composer_host), 0)

        self.sidebar.newChatRequested.connect(self.new_chat)
        self.sidebar.sessionSelected.connect(self.open_session)
        self.sidebar.sessionDeleteRequested.connect(self.delete_session)
        self.sidebar.sessionRenamed.connect(self.rename_session)
        self.sidebar.settingsRequested.connect(self.open_settings)
        self.composer.submitted.connect(self.generationRequested.emit)
        self.statusBar().showMessage("새 채팅을 시작해 보세요.")
        self.reload_theme()

    def bind_controller(self, controller):
        self.controller = controller
        if self.session_manager is None:
            self.session_manager = controller.session_manager

    def closeEvent(self, event):
        try:
            if self.controller is not None:
                self.controller.flush_sessions()
            elif self.session_manager is not None:
                self.session_manager.flush()
        except Exception:
            logger.exception("앱 종료 시 세션 저장 실패")
        super().closeEvent(event)

    # ----- UI-only helpers -----
    def _refresh_sidebar(self):
        if self.session_manager is not None:
            selected = self.current_session.id if self.current_session else None
            self.sidebar.set_sessions(self.session_manager.sessions, selected)

    def _set_status_label(self, text, state="connected"):
        self.status_label.setText(text)
        self.status_label.setProperty("state", state)
        style = self.status_label.style()
        style.unpolish(self.status_label)
        style.polish(self.status_label)
        self.status_label.update()

    def set_generation_busy(self, busy):
        self.composer.set_busy(bool(busy))

    def add_ai_text(self, text):
        self.chat_view.add_ai_text(text)

    def info_message(self, title, text):
        QMessageBox.information(self, title, text)

    def warning_message(self, title, text):
        QMessageBox.warning(self, title, text)

    def confirm_delete_session(self, title):
        answer = QMessageBox.question(
            self, "대화 삭제", f"'{title}' 대화를 삭제할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    # ----- controller delegates (compatibility facade) -----
    def new_chat(self, auto=False):
        if self.controller:
            return self.controller.new_chat(auto=auto)
        return None

    def open_session(self, session_id):
        if self.controller:
            return self.controller.open_session(session_id)
        return None

    def delete_session(self, session_id):
        if self.controller:
            return self.controller.delete_session(session_id)
        return False

    def rename_session(self, session_id, title):
        if self.controller:
            return self.controller.rename_session(session_id, title)
        return False

    def ensure_user_message(self, text, mood, art_style, idea_value=None, update_title=True):
        if self.controller:
            return self.controller.ensure_user_message(text, mood, art_style, idea_value, update_title)
        return None

    # ----- generation UI adapter -----
    def show_generation_message(self, data):
        return self.chat_view.show_generation_message(data)

    def update_generation(self, message_id, message, current, total, session_id=None):
        self.chat_view.update_generation(message_id, message, current, total)

    def begin_panel_generation(self, message_id, index, message):
        self.chat_view.begin_panel_generation(message_id, message, index)

    def begin_final_composition(self, message_id, message):
        self.chat_view.begin_final_composition(message_id, message)

    def complete_story_plan(self, message_id, summary):
        self.chat_view.show_story_plan(message_id, summary)

    def complete_panel_generation(self, message_id, index, path, dialogue="", dialogue_status="", session_id=None):
        self.chat_view.complete_panel_generation(message_id, index, path, dialogue, dialogue_status)

    def begin_panel_regeneration(self, panel_index, revision="", session=None):
        if session is not None:
            self.chat_view.begin_panel_regeneration(session)
            self._generating_session_id = session.id
            self._set_status_label("● AI 작업 중", "busy")
        return self.controller.active_message_id if self.controller else None

    def add_panel_compose_message(self, session):
        return self.controller.active_message_id if self.controller else None

    def finish_panel_regeneration(self, message_id, panel_index, comic, session=None):
        if session is not None:
            self.chat_view.finish_panel_regeneration(session, comic, panel_index)
        self._generating_session_id = None
        self.set_generation_busy(False)
        self._refresh_sidebar()
        self._set_status_label("● 생성 완료", "done")
        self.statusBar().showMessage(f"{panel_index}컷 재생성과 최종 합성이 완료되었습니다.", 4000)

    def finish_generation(self, message_id, comic, session=None):
        if session is not None:
            self.chat_view.finish_generation(session, comic, message_id)
            self.current_session = session
        self.set_generation_busy(False)
        self._generating_session_id = None
        self._refresh_sidebar()
        self._set_status_label("● 생성 완료", "done")
        self.statusBar().showMessage("4컷 만화가 완성되었습니다.", 4000)

    def fail_generation(self, message_id, message, session=None):
        self.chat_view.fail_generation(message_id, message, session)
        self.set_generation_busy(False)
        self._generating_session_id = None
        self._set_status_label("● 생성 오류", "error")
        self._refresh_sidebar()

    def cancel_generation_ui(self, message_id, session=None):
        self.chat_view.cancel_generation_ui(message_id, session)
        self.set_generation_busy(False)
        self._generating_session_id = None
        state = "connected" if all(self._server_state) else "error"
        self._set_status_label("● AI 서버 연결됨" if all(self._server_state) else "● AI 서버 확인 필요", state)
        self._refresh_sidebar()

    def restore_panel_result_message(self, session):
        self.chat_view.restore_panel_result_message(session)

    def _on_cancel_requested(self):
        self.cancelRequested.emit()

    # ----- file save / server status / settings -----
    def save_comic(self, comic):
        path = getattr(comic, "output_path", "")
        if not path or not Path(path).exists():
            self.warning_message("저장할 이미지 없음", "완성된 4컷 이미지를 찾을 수 없습니다.")
            return
        target, _ = QFileDialog.getSaveFileName(self, "4컷 만화 저장", "4cut.png", "PNG (*.png)")
        if not target:
            return
        try:
            shutil.copy2(path, target)
            self.statusBar().showMessage(f"이미지를 저장했습니다: {target}", 4000)
        except OSError:
            logger.exception("완성 이미지 저장 실패: %s", target)
            self.warning_message("저장 실패", "이미지를 저장하지 못했습니다. 대상 폴더의 권한과 여유 공간을 확인해 주세요.")

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
        if self.settings_dialog is not None:
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
        except Exception:
            logger.exception("설정창을 열지 못했습니다.")
            self.warning_message("설정창 오류", "설정창을 열 수 없습니다. 설정 파일과 UI 파일을 확인해 주세요.")
        finally:
            self.settings_dialog = None
