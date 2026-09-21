from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QMessageBox
from ui.idea.idea_section import IdeaSection
from ui.generation.generation_section import GenerationSection
from ui.preview.preview_section import PreviewSection
from ui.result.result_section import ResultSection
from settings.settings_window import SettingsWindow


class MainWindow(QMainWindow):
    settingsApplied = Signal()

    def __init__(self, settings_manager, lm_factory, comfy_factory, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        ui_path = Path(__file__).resolve().parent / "main_window.ui"
        self.form = loader.load(str(ui_path), None)
        if self.form is None:
            raise RuntimeError(f"UI 파일 로드 실패: {ui_path}")
        self.setWindowTitle(self.form.windowTitle())
        self.resize(self.form.size())
        self.setCentralWidget(self.form.centralwidget)
        self.setMenuBar(self.form.menubar)
        self.setStatusBar(self.form.statusbar)

        self.idea = IdeaSection(); self.generation = GenerationSection()
        self.preview = PreviewSection(); self.result = ResultSection()
        self._put(self.form.ideaContainer, self.idea)
        self._put(self.form.generationContainer, self.generation)
        self._put(self.form.previewContainer, self.preview)
        self._put(self.form.resultContainer, self.result)

        self.settings_manager = settings_manager
        self.lm_factory = lm_factory
        self.comfy_factory = comfy_factory
        self.settings_dialog = None
        self.form.actionAISettings.triggered.connect(self.open_settings)

    def _put(self, container, widget):
        layout = container.layout()
        if layout is None:
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

    def open_settings(self):
        if self.settings_dialog is not None:
            self.settings_dialog.form.raise_()
            self.settings_dialog.form.activateWindow()
            return
        try:
            self.settings_dialog = SettingsWindow(self.settings_manager, self.lm_factory, self.comfy_factory, self)
            result = self.settings_dialog.exec()
            if result:
                self.settingsApplied.emit()
                self.statusBar().showMessage("설정이 저장되었습니다. 다음 생성부터 적용됩니다.", 4000)
        except Exception as e:
            QMessageBox.critical(self, "설정창 오류", f"설정창을 열 수 없습니다.\n\n{e}")
        finally:
            self.settings_dialog = None
