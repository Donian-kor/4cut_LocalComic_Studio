from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout


class GenerationSection(QWidget):
    cancelRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        ui_path = Path(__file__).resolve().parent / "generation_section.ui"
        self.form = loader.load(str(ui_path), None)
        if self.form is None:
            raise RuntimeError(f"UI 파일 로드 실패: {ui_path}")
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(self.form)
        self.form.cancelButton.clicked.connect(self.cancelRequested.emit)

    def set_generating(self, generating):
        self.form.cancelButton.setEnabled(generating)

    def set_status(self, message, current, total):
        self.form.statusLabel.setText(message)
        self.form.progressBar.setMaximum(max(1, total))
        self.form.progressBar.setValue(max(0, min(current, total)))
        if current <= 0:
            self.form.stepLabel.setText("이야기 구성 → 4컷 생성 → 대사 → 합성")
        elif current < total:
            self.form.stepLabel.setText(f"4컷 생성 중 · {current}/{total}컷 완료")
        else:
            self.form.stepLabel.setText("마무리 중 · 완성된 4컷을 준비하고 있어요")
