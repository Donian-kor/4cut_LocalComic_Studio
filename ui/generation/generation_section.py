from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout

class GenerationSection(QWidget):
    cancelRequested = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        self.form = loader.load(str(Path(__file__).parent / "generation_section.ui"), None)
        if self.form is None:
            raise RuntimeError("UI 파일 로드 실패: generation_section.ui")
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(self.form)
        self.form.cancelButton.clicked.connect(self.cancelRequested.emit)

    def set_generating(self, generating):
        self.form.cancelButton.setEnabled(generating)

    def set_status(self, message, current, total):
        self.form.statusLabel.setText(message)
        self.form.progressBar.setMaximum(total)
        self.form.progressBar.setValue(current)
