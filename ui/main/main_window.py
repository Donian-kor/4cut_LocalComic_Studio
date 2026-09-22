from pathlib import Path
from PySide6.QtCore import Signal, QThread
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QMessageBox
from ui.idea.idea_section import IdeaSection
from ui.generation.generation_section import GenerationSection
from ui.preview.preview_section import PreviewSection
from ui.result.result_section import ResultSection
from settings.settings_window import SettingsWindow
from settings.model_manager import ImageModelManager


class ServerStatusWorker(QThread):
    checked = Signal(bool, bool, str)

    def __init__(self, lm_factory, comfy_factory, settings_manager, parent=None):
        super().__init__(parent)
        self.lm_factory = lm_factory
        self.comfy_factory = comfy_factory
        self.settings_manager = settings_manager

    def run(self):
        lm_ok = False
        comfy_ok = False
        errors = []
        try:
            lm = self.lm_factory(dict(self.settings_manager.section("lmstudio")))
            lm.test_connection(timeout=2)
            lm_ok = True
        except Exception as e:
            errors.append(f"LM Studio: {e}")
        try:
            comfy = self.comfy_factory(dict(self.settings_manager.section("comfyui")))
            comfy.test_connection(timeout=2)
            comfy_ok = True
        except Exception as e:
            errors.append(f"ComfyUI: {e}")
        self.checked.emit(lm_ok, comfy_ok, " / ".join(errors))


class MainWindow(QMainWindow):
    settingsApplied = Signal()

    DARK_QSS = """
    * { font-family: 'Malgun Gothic', 'Noto Sans KR', sans-serif; }
    QMainWindow, QWidget { background: #0b0d13; color: #f5f7fb; }
    QFrame#headerFrame { background: #10131c; border-bottom: 1px solid #252a38; }
    QLabel#logoLabel { color: #ffffff; font-size: 20px; font-weight: 800; }
    QLabel#taglineLabel { color: #7f8799; font-size: 12px; }
    QLabel#saveStatusLabel { color: #cbd2e1; font-size: 12px; padding: 7px 10px; background: #151a24; border: 1px solid #293043; border-radius: 8px; }
    QPushButton { background: #1a1f2c; color: #e8ebf2; border: 1px solid #303748; border-radius: 9px; padding: 10px 16px; font-weight: 600; }
    QPushButton:hover { background: #22283a; border-color: #59627a; }
    QPushButton:pressed { background: #171b26; }
    QPushButton:disabled { color: #646b7a; background: #141720; border-color: #222735; }
    QPushButton#settingsButton { border: none; background: transparent; color: #9aa2b3; }
    QPushButton#settingsButton:hover { background: #1b202d; color: #ffffff; }
    QPlainTextEdit { background: #131720; border: 1px solid #303748; border-radius: 12px; color: #f5f7fb; padding: 16px; font-size: 15px; selection-background-color: #6366f1; }
    QPlainTextEdit:focus { border: 1px solid #6366f1; }
    QComboBox { background: #131720; border: 1px solid #303748; border-radius: 8px; padding: 8px 12px; color: #e9ecf4; min-width: 100px; }
    QComboBox:hover { border-color: #4b556d; }
    QComboBox QAbstractItemView { background: #171b25; color: #e9ecf4; selection-background-color: #2c3260; }
    QLabel#eyebrowLabel { color: #818cf8; font-size: 12px; font-weight: 800; letter-spacing: 1px; }
    QLabel#titleLabel { color: #ffffff; font-size: 36px; font-weight: 800; }
    QLabel#subtitleLabel { color: #9199aa; font-size: 14px; }
    QLabel#styleLabel { color: #9ca4b5; font-size: 12px; font-weight: 700; }
    QPushButton#generateButton { background: #6366f1; border: none; color: white; font-size: 16px; font-weight: 800; border-radius: 12px; }
    QPushButton#generateButton:hover { background: #7477f5; }
    QLabel#hintLabel { color: #687184; font-size: 12px; }
    QLabel#iconLabel { color: #818cf8; font-size: 42px; }
    QFrame#generationContainer QLabel#titleLabel { font-size: 28px; }
    QFrame#generationContainer QLabel#statusLabel { color: #c3c8d5; font-size: 16px; }
    QLabel#stepLabel { color: #6f7789; font-size: 12px; }
    QProgressBar { background: #1b202b; border: none; border-radius: 4px; }
    QProgressBar::chunk { background: #6366f1; border-radius: 4px; }
    QFrame#previewContainer QLabel#titleLabel { font-size: 22px; font-weight: 800; }
    QFrame#previewContainer QLabel#subtitleLabel { color: #7e8799; font-size: 12px; }
    QLabel#imageLabel { background: #0e1118; border: 1px solid #252b3a; border-radius: 12px; }
    QLabel#resultLabel { color: #cdd2df; font-size: 14px; font-weight: 700; }
    QFrame#revisionFrame { background: #121620; border: 1px solid #292f40; border-radius: 12px; }
    QLabel#revisionLabel { color: #bfc5d3; font-size: 13px; font-weight: 700; }
    QPushButton#revisionButton { background: #2a2f5d; border-color: #4b50a2; color: #e6e7ff; }
    QPushButton#revisionButton:hover { background: #343a70; }
    QStatusBar { background: #10131c; color: #7d8597; }
    """

    def __init__(self, settings_manager, lm_factory, comfy_factory, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        ui_path = Path(__file__).resolve().parent / "main_window.ui"
        self.form = loader.load(str(ui_path), None)
        if self.form is None:
            raise RuntimeError(f"UI 파일 로드 실패: {ui_path}")
        # 앱 내부 헤더에 프로그램명이 있으므로 OS 제목 표시줄의 중복 텍스트는 제거한다.
        self.setWindowTitle("")
        self.resize(1100, 820)
        self.setMinimumSize(self.form.minimumSize())
        self.setCentralWidget(self.form.centralwidget)
        self.setMenuBar(self.form.menubar)
        self.setStatusBar(self.form.statusbar)
        self.setStyleSheet(self.DARK_QSS)

        self.settings_manager = settings_manager
        self.lm_factory = lm_factory
        self.comfy_factory = comfy_factory
        self.settings_dialog = None
        self._server_worker = None
        self._server_state = (False, False)

        self.idea = IdeaSection(self.settings_manager)
        self.generation = GenerationSection()
        self.preview = PreviewSection()
        self.result = ResultSection()
        self._put(self.form.ideaContainer, self.idea)
        self._put(self.form.generationContainer, self.generation)
        self._put(self.form.previewContainer, self.preview)
        self._put(self.form.resultContainer, self.result)

        self.form.settingsButton.clicked.connect(self.open_settings)
        self.form.actionAISettings.triggered.connect(self.open_settings)
        self.show_idea_page()
        self.refresh_server_status()

    def _put(self, container, widget):
        layout = container.layout()
        if layout is None:
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

    def refresh_server_status(self):
        if self._server_worker and self._server_worker.isRunning():
            return
        self.form.saveStatusLabel.setText("● AI 서버 확인 중...")
        self._server_worker = ServerStatusWorker(
            self.lm_factory, self.comfy_factory, self.settings_manager, self
        )
        self._server_worker.checked.connect(self._on_server_status)
        self._server_worker.finished.connect(self._release_server_worker)
        self._server_worker.start()

    def _release_server_worker(self):
        self._server_worker = None

    def _on_server_status(self, lm_ok, comfy_ok, errors):
        self._server_state = (lm_ok, comfy_ok)
        if lm_ok and comfy_ok:
            self.form.saveStatusLabel.setText("● AI 서버 연결됨")
        elif lm_ok or comfy_ok:
            self.form.saveStatusLabel.setText("● 일부 AI 서버 연결됨")
        else:
            self.form.saveStatusLabel.setText("● AI 서버 미연결")
        if errors and self.form.pageStack.currentWidget() == self.form.ideaPage:
            self.statusBar().showMessage("AI 서버 연결을 확인하세요. 설정에서 주소와 연결 상태를 확인할 수 있습니다.", 6000)

    def show_idea_page(self):
        self.form.pageStack.setCurrentWidget(self.form.ideaPage)
        self.refresh_server_status()

    def show_generation_page(self):
        self.form.pageStack.setCurrentWidget(self.form.generationPage)
        self.form.saveStatusLabel.setText("● AI 작업 중")

    def show_result_page(self):
        self.form.pageStack.setCurrentWidget(self.form.resultPage)
        self.form.saveStatusLabel.setText("● 결과 준비됨")

    def open_settings(self):
        if self.settings_dialog is not None:
            self.settings_dialog.form.raise_()
            self.settings_dialog.form.activateWindow()
            return
        try:
            self.settings_dialog = SettingsWindow(
                self.settings_manager, self.lm_factory, self.comfy_factory, self
            )
            result = self.settings_dialog.form.exec()
            if result:
                self.settingsApplied.emit()
                self.form.saveStatusLabel.setText("● 설정 저장됨 · 서버 확인 중...")
                self.statusBar().showMessage("설정이 저장되었습니다. 서버 연결을 다시 확인합니다.", 4000)
                self.refresh_server_status()
        except Exception as e:
            QMessageBox.critical(self, "설정창 오류", f"설정창을 열 수 없습니다.\n\n{e}")
        finally:
            self.settings_dialog = None
