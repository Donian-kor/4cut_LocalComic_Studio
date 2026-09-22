from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout


class IdeaSection(QWidget):
    generateRequested = Signal(str, str)

    STYLE_PRESETS = {
        "자동": "",
        "개그": "clean anime cel shading, crisp lineart, flat colors, expressive comedic timing, consistent character design",
        "일상": "clean anime cel shading, crisp lineart, flat colors, warm everyday atmosphere, consistent character design",
        "로맨스": "daily romance manga, soft pastel palette, gentle mood, cute character design, warm lighting",
        "판타지": "fantasy anime illustration, clean lineart, vivid colors, cinematic atmosphere, consistent character design",
    }

    def __init__(self, settings_manager=None, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        loader = QUiLoader()
        ui_path = Path(__file__).resolve().parent / "idea_section.ui"
        self.form = loader.load(str(ui_path), None)
        if self.form is None:
            raise RuntimeError(f"UI 파일 로드 실패: {ui_path}")
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(self.form)
        self.form.generateButton.clicked.connect(self._emit)
        self._sync_style_items()
        self._load_style()
        self.form.styleEdit.currentTextChanged.connect(self._on_style_changed)

    def _sync_style_items(self):
        # UI 파일과 Python 프리셋 항목 동기화 보장
        current = self.form.styleEdit.currentText()
        if self.form.styleEdit.count() == 0:
            self.form.styleEdit.addItems(list(self.STYLE_PRESETS.keys()))
        if current:
            self.form.styleEdit.setCurrentText(current)

    def _load_style(self):
        if self.settings_manager is None:
            return
        try:
            saved = str(self.settings_manager.section("general").get("style_prompt", ""))
            for label, prompt in self.STYLE_PRESETS.items():
                if saved.lower() == prompt.lower():
                    self.form.styleEdit.setCurrentText(label)
                    return
            self.form.styleEdit.setCurrentText("자동")
        except Exception:
            self.form.styleEdit.setCurrentText("자동")

    def _on_style_changed(self, label):
        if self.settings_manager is None:
            return
        prompt = self.STYLE_PRESETS.get(label, "")
        try:
            self.settings_manager.section("general")["style_prompt"] = prompt
            self.settings_manager.save()
        except Exception:
            pass

    def _emit(self):
        idea = self.form.ideaEdit.toPlainText().strip()
        if not idea:
            self.form.ideaEdit.setFocus()
            return
        label = self.form.styleEdit.currentText().strip() or "자동"
        style = self.STYLE_PRESETS.get(label, label)
        self.generateRequested.emit(idea, style)

    def set_enabled(self, enabled):
        self.form.generateButton.setEnabled(enabled)
        self.form.ideaEdit.setEnabled(enabled)
        self.form.styleEdit.setEnabled(enabled)
