from pathlib import Path
import shutil
from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFileDialog


class ResultSection(QWidget):
    regenerateRequested = Signal()
    revisionRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        ui_path = Path(__file__).resolve().parent / "result_section.ui"
        self.form = loader.load(str(ui_path), None)
        if self.form is None:
            raise RuntimeError(f"UI 파일 로드 실패: {ui_path}")
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(self.form)
        self.form.regenerateButton.clicked.connect(self.regenerateRequested.emit)
        self.form.saveButton.clicked.connect(self.save_result)
        self.form.revisionButton.clicked.connect(self._emit_revision)
        self.comic = None

    def show_result(self, comic):
        self.comic = comic
        self.form.resultLabel.setText(f"{comic.title} · 4컷 완성")
        self.form.revisionEdit.clear()

    def _emit_revision(self):
        text = self.form.revisionEdit.toPlainText().strip()
        if text:
            self.revisionRequested.emit(text)
            self.form.revisionButton.setEnabled(False)

    def set_revision_enabled(self, enabled):
        self.form.revisionButton.setEnabled(enabled)

    def save_result(self):
        if not self.comic or not self.comic.output_path or not Path(self.comic.output_path).exists():
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "4컷 만화 저장", "4cut.png", "PNG (*.png)"
        )
        if target:
            shutil.copy2(self.comic.output_path, target)
