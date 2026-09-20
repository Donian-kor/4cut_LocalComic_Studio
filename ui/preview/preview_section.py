from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

class PreviewSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        self.form = loader.load("ui/preview/preview_section.ui", None)
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(self.form)

    def show_comic(self, comic):
        if comic.output_path:
            pix = QPixmap(comic.output_path)
            self.form.imageLabel.setPixmap(
                pix.scaled(
                    self.form.imageLabel.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
