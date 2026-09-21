from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout

class IdeaSection(QWidget):
    generateRequested = Signal(str, str)
    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        self.form = loader.load(str(Path(__file__).parent / "idea_section.ui"), None)
        if self.form is None:
            raise RuntimeError("UI 파일 로드 실패: idea_section.ui")
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(self.form)
        self.form.generateButton.clicked.connect(self._emit)

    def _emit(self):
        idea = self.form.ideaEdit.toPlainText().strip()
        if not idea:
            self.form.ideaEdit.setFocus()
            return
        self.generateRequested.emit(idea, self.form.styleEdit.text().strip())

    def set_enabled(self, enabled):
        self.form.generateButton.setEnabled(enabled)
        self.form.ideaEdit.setEnabled(enabled)
        self.form.styleEdit.setEnabled(enabled)
