from pathlib import Path
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


class PreviewSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        self.form = loader.load(str(Path(__file__).parent / "preview_section.ui"), None)
        if self.form is None:
            raise RuntimeError("UI 파일 로드 실패: preview_section.ui")
        wrapper = QVBoxLayout(self); wrapper.setContentsMargins(0, 0, 0, 0); wrapper.addWidget(self.form)
        self._pixmap = None

    def show_comic(self, comic):
        if comic.output_path:
            self._pixmap = QPixmap(comic.output_path)
            self._refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        if self._pixmap and not self._pixmap.isNull():
            self.form.imageLabel.setPixmap(self._pixmap.scaled(
                self.form.imageLabel.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
