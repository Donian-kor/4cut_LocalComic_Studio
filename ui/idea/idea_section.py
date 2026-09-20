from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout

class IdeaSection(QWidget):
    generateRequested = Signal(str, str)
    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        self.form = loader.load("ui/idea/idea_section.ui", None)
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(self.form)
        self.form.generateButton.clicked.connect(self._emit)

    def _emit(self):
        self.generateRequested.emit(self.form.ideaEdit.toPlainText(), self.form.styleEdit.text())

    def set_enabled(self, enabled):
        self.form.generateButton.setEnabled(enabled)
        self.form.ideaEdit.setEnabled(enabled)
        self.form.styleEdit.setEnabled(enabled)
