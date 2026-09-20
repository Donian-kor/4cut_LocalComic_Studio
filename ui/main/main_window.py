from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QVBoxLayout
from ui.idea.idea_section import IdeaSection
from ui.generation.generation_section import GenerationSection
from ui.preview.preview_section import PreviewSection
from ui.result.result_section import ResultSection
from settings.settings_window import SettingsWindow

class MainWindow(QMainWindow):
    def __init__(self, settings_manager, lm_factory, comfy_factory, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        self.form = loader.load("ui/main/main_window.ui", self)
        self.setWindowTitle(self.form.windowTitle())
        self.resize(self.form.size())

        central = self.form.centralwidget
        self.setCentralWidget(central)
        self.setMenuBar(self.form.menubar)
        self.setStatusBar(self.form.statusbar)

        self.idea = IdeaSection()
        self.generation = GenerationSection()
        self.preview = PreviewSection()
        self.result = ResultSection()

        self._put(self.form.ideaContainer, self.idea)
        self._put(self.form.generationContainer, self.generation)
        self._put(self.form.previewContainer, self.preview)
        self._put(self.form.resultContainer, self.result)

        self.settings_manager = settings_manager
        self.lm_factory = lm_factory
        self.comfy_factory = comfy_factory
        self.form.actionAISettings.triggered.connect(self.open_settings)

    def _put(self, container, widget):
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

    def open_settings(self):
        dlg = SettingsWindow(
            self.settings_manager,
            self.lm_factory,
            self.comfy_factory,
            self
        )
        if dlg.exec():
            # Settings are persisted by the dialog.
            self.statusBar().showMessage("설정이 저장되었습니다.", 3000)
