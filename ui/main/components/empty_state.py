from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFrame, QVBoxLayout


class EmptyState(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("emptyState")
        loader = QUiLoader()
        form = loader.load(str(Path(__file__).with_name("empty_state.ui")), self)
        if form is None:
            raise RuntimeError("UI 파일 로드 실패: empty_state.ui")
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(form)
        self.form = form
