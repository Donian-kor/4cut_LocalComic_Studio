from pathlib import Path
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


class PreviewSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        ui_path = Path(__file__).resolve().parent / "preview_section.ui"
        self.form = loader.load(str(ui_path), None)
        if self.form is None:
            raise RuntimeError(f"UI 파일 로드 실패: {ui_path}")
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(self.form)
        self._pixmap = None

    def show_comic(self, comic):
        if comic.output_path:
            pixmap = QPixmap(comic.output_path)
            if not pixmap.isNull():
                self._pixmap = pixmap
                self._refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        if self._pixmap and not self._pixmap.isNull():
            target = self.form.imageLabel.size()
            if target.width() > 0 and target.height() > 0:
                self.form.imageLabel.setPixmap(
                    self._pixmap.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
