from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFileDialog
import shutil


class ResultSection(QWidget):
    regenerateRequested = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        self.form = loader.load(str(Path(__file__).parent / "result_section.ui"), None)
        if self.form is None:
            raise RuntimeError("UI 파일 로드 실패: result_section.ui")
        wrapper = QVBoxLayout(self); wrapper.setContentsMargins(0, 0, 0, 0); wrapper.addWidget(self.form)
        self.form.regenerateButton.clicked.connect(self.regenerateRequested.emit)
        self.form.saveButton.clicked.connect(self.save_result)
        self.comic = None

    def show_result(self, comic):
        self.comic = comic
        self.form.resultLabel.setText(f"완성: {comic.title}\n저장 위치: {comic.output_path}")

    def save_result(self):
        if not self.comic or not self.comic.output_path or not Path(self.comic.output_path).exists():
            return
        target, _ = QFileDialog.getSaveFileName(self, "4컷 만화 저장", "4cut.png", "PNG (*.png)")
        if target:
            shutil.copy2(self.comic.output_path, target)
