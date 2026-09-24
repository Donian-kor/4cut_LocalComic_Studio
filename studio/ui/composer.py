from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFrame, QVBoxLayout

from studio.ui.idea_section import IdeaSection


class Composer(QFrame):
    submitted = Signal(str, str, str, str)

    def _icon_path(self):
        # studio/ui/composer.py → studio/ → 프로젝트 루트 (2단계 상위)
        return Path(__file__).resolve().parents[2] / "resources" / "send_pen.svg"

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.setObjectName("composerFrame")
        loader = QUiLoader()
        form = loader.load(str(Path(__file__).with_name("composer.ui")), self)
        if form is None:
            raise RuntimeError("UI 파일 로드 실패: composer.ui")
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(form)
        self.form = form
        self.idea = self.form.ideaEdit
        self.mood = self.form.moodCombo
        self.art = self.form.artCombo
        self.send = self.form.sendButton
        self.idea.setObjectName("composerEdit")
        self.mood.setObjectName("composerCombo")
        self.art.setObjectName("composerCombo")
        self.send.setObjectName("sendButton")
        two_line_height = (self.idea.fontMetrics().lineSpacing() * 2) + 30
        self.idea.setMinimumHeight(two_line_height)
        self.idea.setMaximumHeight(two_line_height)
        self.idea.installEventFilter(self)
        self.mood.addItems(list(IdeaSection.STYLE_PRESETS.keys()))
        self.art.addItems(list(IdeaSection.ART_STYLE_PRESETS.keys()))
        self.send.setIconSize(QSize(20, 20))
        self.send.clicked.connect(self._submit)
        self.set_busy(False)
        self.setEnabled(True)

    def eventFilter(self, obj, event):
        if obj is self.idea and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self._submit()
                return True
        return super().eventFilter(obj, event)

    def _submit(self):
        text = self.idea.toPlainText().strip()
        if not text:
            self.idea.setFocus()
            return
        mood = self.mood.currentText() or "자동"
        art = self.art.currentText() or "캐주얼 만화"
        mood_prompt = IdeaSection.STYLE_PRESETS.get(mood, "")
        art_prompt = IdeaSection.ART_STYLE_PRESETS.get(art, "")
        style_prompt = ", ".join([x for x in (art_prompt, mood_prompt) if x])
        self.submitted.emit(text, style_prompt, mood, art)

    def set_busy(self, busy):
        self.idea.setEnabled(not busy)
        self.mood.setEnabled(not busy)
        self.art.setEnabled(not busy)
        self.send.setEnabled(not busy)
        if busy:
            self.send.setIcon(QIcon())
            self.send.setText("…")
        else:
            if self._icon_path().exists():
                self.send.setIcon(QIcon(str(self._icon_path())))
                self.send.setText("")
            else:
                self.send.setIcon(QIcon())
                self.send.setText("↑")

    def load_session_options(self, session):
        self.mood.setCurrentText(session.mood or "자동")
        self.art.setCurrentText(session.art_style or "캐주얼 만화")
