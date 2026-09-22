from pathlib import Path
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QComboBox

class IdeaSection(QWidget):
    generateRequested = Signal(str, str)

    STYLE_PRESETS = [
        ("기본", "clean anime cel shading, crisp lineart, flat colors, consistent character design"),
        ("kr웹툰", "Korean webtoon style, clean lineart, soft shading, vibrant colors, manga-inspired composition"),
        ("일본만화", "Japanese manga style, bold ink lines, screentone shading, dynamic expressions, anime aesthetic"),
        ("서양판타지", "Western fantasy illustration, detailed rendering, painterly lighting, epic atmosphere, realistic proportions"),
        ("일상로맨스", "Daily romance manga, soft pastel palette, gentle mood, cute character design, warm lighting"),
    ]

    def __init__(self, settings_manager=None, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        loader = QUiLoader()
        self.form = loader.load(str(Path(__file__).parent / "idea_section.ui"), None)
        if self.form is None:
            raise RuntimeError("UI 파일 로드 실패: idea_section.ui")
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(self.form)
        self.form.generateButton.clicked.connect(self._emit)

        # styleEdit을 QComboBox로 교체
        self._replace_style_edit()

        # 초기 스타일 설정 (설정 저장소에서)
        self._load_style()

    def _replace_style_edit(self):
        """idea_section.ui의 QLineEdit(styleEdit)를 QComboBox로 교체한다."""
        old = self.form.styleEdit
        if old is None:
            return

        parent_widget = old.parentWidget()
        if parent_widget is None:
            return

        layout = parent_widget.layout()
        if layout is None:
            return

        # QComboBox 생성
        combo = QComboBox(parent_widget)
        combo.setObjectName("styleEdit")
        combo.setEditable(True)
        combo.setEditable(True)  # 직접 입력도 가능하도록
        for name, _prompt in self.STYLE_PRESETS:
            combo.addItem(name)

        # QLineEdit이었던 곳의 인덱스를 찾아 교체
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget() is old:
                # old widget 제거
                layout.removeWidget(old)
                old.deleteLater()
                # combo 삽입
                layout.insertWidget(i, combo)
                self.form.styleEdit = combo
                break

        # 텍스트 변경 시 일반 설정에 저장
        combo.currentTextChanged.connect(self._on_style_changed)

    def _load_style(self):
        """설정 저장소에서 현재 스타일을 불러온다."""
        if self.settings_manager is None:
            return
        try:
            g = self.settings_manager.section("general")
            style_prompt = str(g.get("style_prompt", ""))
            for name, prompt in self.STYLE_PRESETS:
                if style_prompt and prompt.lower() == style_prompt.lower():
                    idx = self.form.styleEdit.findText(name)
                    if idx >= 0:
                        self.form.styleEdit.setCurrentIndex(idx)
                    return
        except Exception:
            pass

    def _on_style_changed(self, text):
        """드롭다운 선택 시 일반 설정에 style_prompt를 저장한다."""
        if self.settings_manager is None:
            return
        try:
            for name, prompt in self.STYLE_PRESETS:
                if name == text:
                    g = self.settings_manager.section("general")
                    g["style_prompt"] = prompt
                    self.settings_manager.save()
                    break
        except Exception:
            pass

    def _emit(self):
        idea = self.form.ideaEdit.toPlainText().strip()
        if not idea:
            self.form.ideaEdit.setFocus()
            return
        self.generateRequested.emit(idea, self.form.styleEdit.currentText().strip())

    def set_enabled(self, enabled):
        self.form.generateButton.setEnabled(enabled)
        self.form.ideaEdit.setEnabled(enabled)
        self.form.styleEdit.setEnabled(enabled)
