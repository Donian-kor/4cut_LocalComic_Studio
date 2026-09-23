from pathlib import Path

from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QInputDialog,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class AspectPixmapLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._render_hint = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(60, 60)

    def set_image(self, path, size=None):
        if path and Path(path).exists():
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                self._pixmap = pixmap
                self._render_hint = size
                self._render()
                return True
        self._pixmap = None
        self._render_hint = size
        self.clear()
        return False

    def _render(self):
        if not self._pixmap or self._pixmap.isNull():
            return
        target = self.size()
        if self._render_hint:
            w = h = self._render_hint
            # Keep the widget's available width when a larger viewport is provided.
            if target.width() > 60:
                w = min(w, target.width())
                h = min(h, max(60, target.height()))
        else:
            w, h = max(60, target.width()), max(60, target.height())
        self.setPixmap(
            self._pixmap.scaled(
                max(60, w),
                max(60, h),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._render()


class ChatBubble(QFrame):
    saveRequested = Signal(object)
    regenerateRequested = Signal()
    revisionRequested = Signal()

    def __init__(self, role="ai", parent=None):
        super().__init__(parent)
        self.role = role
        self.setObjectName("chatBubbleAi" if role == "ai" else "chatBubbleUser")
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 12, 16, 12)
        self.layout.setSpacing(8)

    def add_text(self, text, muted=False):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if muted:
            label.setObjectName("mutedText")
        self.layout.addWidget(label)
        return label


class ChatMessageRow(QWidget):
    def __init__(self, role="ai", parent=None):
        super().__init__(parent)
        self.role = role
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 6, 16, 6)
        row.setSpacing(12)
        self.badge = QLabel("AI" if role == "ai" else "사용자")
        self.badge.setObjectName("aiBadge" if role == "ai" else "userBadge")
        self.bubble = ChatBubble(role)
        row.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(self.bubble, 0, Qt.AlignmentFlag.AlignTop)
        row.addStretch(1)
        if role == "user":
            row.removeWidget(self.badge)
            row.removeWidget(self.bubble)
            row.addStretch(1)
            row.addWidget(self.bubble, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignTop)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        max_width = max(320, min(800, int(self.width() * 0.78)))
        self.bubble.setMaximumWidth(max_width)


class GenerationCard(QFrame):
    """현재 진행 중인 단 한 개의 생성 단계만 표시한다.

    1컷 생성 중에는 1컷 카드 하나만 보이며, 완료되면 외부에서 PanelResultCard를
    새로 추가한 후 이 카드를 다음 컷 생성용으로 재사용/교체할 수 있다.
    """

    cancelRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("generationCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._pulse = 0.15
        self._pulse_animation = QPropertyAnimation(self, b"pulse", self)
        self._pulse_animation.setDuration(1500)
        self._pulse_animation.setStartValue(0.12)
        self._pulse_animation.setKeyValueAt(0.5, 1.0)
        self._pulse_animation.setEndValue(0.12)
        self._pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_animation.setLoopCount(-1)

        self.main = QVBoxLayout(self)
        self.main.setContentsMargins(16, 14, 16, 14)
        self.main.setSpacing(10)

        header = QHBoxLayout()
        self.status = QLabel("생성을 준비하는 중…")
        self.status.setObjectName("generationStatus")
        self.timer = QLabel("00:00")
        self.timer.setObjectName("generationTimer")
        header.addWidget(self.status)
        header.addStretch(1)
        header.addWidget(self.timer)
        self.main.addLayout(header)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(7)
        self.main.addWidget(self.progress)

        self.panel_badge = QLabel("준비 중")
        self.panel_badge.setObjectName("generationPanelBadge")
        self.panel_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main.addWidget(self.panel_badge)

        self.preview = QFrame()
        self.preview.setObjectName("generationPreview")
        preview_layout = QVBoxLayout(self.preview)
        preview_layout.setContentsMargins(16, 22, 16, 22)
        preview_layout.setSpacing(8)

        self.preview_title = QLabel("스토리를 구성하고 있어요")
        self.preview_title.setObjectName("generationPreviewTitle")
        self.preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_title)

        self.preview_text = QLabel("잠시만 기다려 주세요…")
        self.preview_text.setObjectName("generationPreviewText")
        self.preview_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_text.setWordWrap(True)
        preview_layout.addWidget(self.preview_text)
        self.main.addWidget(self.preview)

        self.step = QLabel("스토리 구성 → 1컷 → 2컷 → 3컷 → 4컷 → 최종 합성")
        self.step.setObjectName("generationStep")
        self.step.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main.addWidget(self.step)

        self.cancel = QPushButton("생성 취소")
        self.cancel.setObjectName("dangerButton")
        self.cancel.clicked.connect(self.cancelRequested.emit)
        self.main.addWidget(self.cancel, 0, Qt.AlignmentFlag.AlignLeft)

        self._elapsed = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def get_pulse(self):
        return self._pulse

    def set_pulse(self, value):
        self._pulse = float(value)
        self.update()

    pulse = Property(float, get_pulse, set_pulse)

    def paintEvent(self, event):
        # 기존 QSS 배경 위에 펄스형 테두리/글로우를 추가한다.
        super().paintEvent(event)
        if not self._pulse_animation.state() == QPropertyAnimation.State.Running:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        base = QColor("#6366f1")
        glow_alpha = int(35 + 115 * self._pulse)
        for width, alpha_mul in ((6, 0.22), (3, 0.55), (1.5, 1.0)):
            color = QColor(base)
            color.setAlpha(max(20, int(glow_alpha * alpha_mul)))
            pen = QPen(color, width)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            margin = width
            rect = self.rect().adjusted(int(margin), int(margin), -int(margin), -int(margin))
            p.drawRoundedRect(rect, 12, 12)

    def start(self):
        self._elapsed = 0
        self.timer.setText("00:00")
        self.cancel.setEnabled(True)
        self.progress.setMaximum(4)
        self.progress.setValue(0)
        self.set_story_mode()
        self._timer.start()
        self._pulse_animation.start()

    def stop(self):
        self._timer.stop()
        self.cancel.setEnabled(False)
        self._pulse_animation.stop()
        self._pulse = 0.0
        self.update()

    def _tick(self):
        self._elapsed += 1
        self.timer.setText(f"{self._elapsed // 60:02d}:{self._elapsed % 60:02d}")

    def set_story_mode(self):
        self.panel_badge.setText("스토리")
        self.preview_title.setText("스토리를 구성하고 있어요")
        self.preview_text.setText("AI가 4컷의 장면과 대사를 준비하고 있습니다…")
        self.step.setText("스토리 구성 → 1컷 → 2컷 → 3컷 → 4컷 → 최종 합성")

    def set_panel_active(self, index):
        if not (1 <= index <= 4):
            return
        self.panel_badge.setText(f"{index} / 4 컷")
        self.preview_title.setText(f"{index}컷 생성중")
        self.preview_text.setText("이미지를 생성하고 대사를 합성하는 중…")
        self.step.setText(
            f"스토리 완료  →  <b>{index}컷 생성중</b>  →  "
            f"{index + 1}컷 → 4컷 → 최종 합성"
        )
        self.progress.setValue(max(0, index - 1))
        self.update()

    def set_compose_mode(self):
        self.panel_badge.setText("FINAL")
        self.preview_title.setText("4컷 최종 합성중")
        self.preview_text.setText("완성된 4개의 컷을 하나의 4컷 만화로 합성하고 있습니다…")
        self.step.setText("1컷 완료 → 2컷 완료 → 3컷 완료 → 4컷 완료 → <b>최종 합성중</b>")
        self.progress.setValue(4)
        self.update()

    def set_status(self, message, current, total):
        self.status.setText(message)
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(max(0, min(current, total)))
        lower = str(message).lower()
        for idx in range(1, 5):
            if f"{idx}컷" in message and "생성 중" in message:
                self.set_panel_active(idx)
                return
        if "합성 중" in message or "합성" in lower:
            self.set_compose_mode()
        elif current <= 0:
            self.set_story_mode()

    def set_failed(self, message):
        self.stop()
        self.status.setText("생성 실패")
        self.panel_badge.setText("오류")
        self.preview_title.setText("생성에 실패했습니다")
        self.preview_text.setText(message or "설정을 확인한 뒤 다시 시도해 주세요.")
        self.step.setText("설정을 확인한 뒤 다시 시도해 주세요.")

    def set_cancelled(self):
        self.stop()
        self.status.setText("생성이 취소되었습니다.")
        self.panel_badge.setText("취소")
        self.preview_title.setText("생성을 중단했습니다")
        self.preview_text.setText("다시 만들려면 새 요청을 보내 주세요.")
        self.step.setText("사용자 요청으로 생성을 중단했습니다.")


class PanelResultCard(QFrame):
    """대사 합성까지 끝난 단일 컷과 개별 재생성/수정 액션을 표시한다."""

    regenerateRequested = Signal(int)
    revisionRequested = Signal(int, str)

    # 대사 합성 상태별 배지 문구 (빈 값은 구버전 세션 호환)
    _STATUS_BADGES = {
        "composited": "✓ 이미지 + 대사 합성 완료",
        "fallback": "✓ 이미지 완료 · 대사 대체 합성",
        "failed": "⚠ 이미지 완료 · 대사 합성 실패",
        "skipped": "✓ 이미지 완료 · 2단계 미설정",
        "none": "✓ 이미지 완료",
    }

    def __init__(self, index, path, dialogue="", status="", parent=None):
        super().__init__(parent)
        self.setObjectName("panelResultCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel(f"{index}컷 완성")
        title.setObjectName("panelResultTitle")
        header.addWidget(title)
        header.addStretch(1)
        badge = QLabel(self._STATUS_BADGES.get(str(status or ""), "✓ 이미지 + 대사 완료"))
        badge.setObjectName("panelDoneBadge")
        header.addWidget(badge)
        layout.addLayout(header)

        self.image = AspectPixmapLabel()
        self.image.setObjectName("panelResultImage")
        self.image.setMinimumHeight(280)
        self.image.setMaximumWidth(760)
        self.image.setMinimumWidth(300)
        if not self.image.set_image(path):
            self.image.setText("이미지를 불러오지 못했습니다.")
        layout.addWidget(self.image)

        if dialogue:
            label = QLabel(dialogue)
            label.setObjectName("panelDialogueText")
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label)

        actions = QHBoxLayout()
        self.regenerate = QPushButton("↻ 이 컷 다시 만들기")
        self.edit = QPushButton("✎ 이 컷 수정")
        self.regenerate.setObjectName("primaryAction")
        self.edit.setObjectName("subtleButton")
        actions.addWidget(self.regenerate)
        actions.addWidget(self.edit)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.regenerate.clicked.connect(lambda: self.regenerateRequested.emit(index))
        self._panel_index = int(index)
        self.edit.clicked.connect(self._request_revision)

    def _request_revision(self):
        text, ok = QInputDialog.getMultiLineText(
            self,
            f"{self._panel_index}컷 수정",
            "수정 요청",
            "예: 표정을 더 크게 웃게 하고, 손에 커피를 들게 해주세요.",
        )
        if ok and text.strip():
            self.revisionRequested.emit(self._panel_index, text.strip())


class ResultCard(QFrame):
    saveRequested = Signal(object)
    regenerateRequested = Signal()

    def __init__(self, comic, parent=None):
        super().__init__(parent)
        self.comic = comic
        self.setObjectName("resultCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(f"{comic.title or '4컷 만화'} · 완성")
        title.setObjectName("resultTitle")
        layout.addWidget(title)

        self.image = AspectPixmapLabel()
        self.image.setObjectName("finalComicImage")
        self.image.setMinimumHeight(320)
        self.image.setMaximumWidth(800)
        self.image.setMinimumWidth(360)
        self.image.set_image(comic.output_path)
        layout.addWidget(self.image)

        actions = QHBoxLayout()
        self.save = QPushButton("↓ 저장")
        self.regenerate = QPushButton("↻ 다시 만들기")
        self.save.setObjectName("primaryAction")
        actions.addWidget(self.save)
        actions.addWidget(self.regenerate)
        actions.addStretch(1)
        layout.addLayout(actions)

        hint = QLabel("각 컷에서 ‘다시 만들기’ 또는 ‘수정’을 눌러 해당 컷만 빠르게 교체할 수 있습니다. 전체 다시 만들기는 모든 컷을 새로 생성합니다.")
        hint.setObjectName("mutedText")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.save.clicked.connect(lambda: self.saveRequested.emit(self.comic))
        self.regenerate.clicked.connect(self.regenerateRequested.emit)

    def update_result(self, comic):
        self.comic = comic
        self.image.set_image(getattr(comic, "output_path", ""))


class ChatScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 22, 0, 22)
        self.content_layout.setSpacing(2)
        self.content_layout.addStretch(1)
        self.setWidget(self.content)

    def append(self, widget):
        # 위젯 추가 전의 하단 근접 상태를 확인한다(레이아웃 갱신 후에는 max가 이미 바뀜).
        near_bottom = self.is_near_bottom()
        self.content_layout.insertWidget(self.content_layout.count() - 1, widget)
        if near_bottom:
            self._maybe_scroll_to_bottom()

    def clear_messages(self):
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            child = item.widget()
            if child:
                child.deleteLater()

    def remove_widget(self, widget):
        if widget is None:
            return
        self.content_layout.removeWidget(widget)
        widget.setParent(None)
        widget.deleteLater()

    def is_near_bottom(self):
        bar = self.verticalScrollBar()
        return bar.value() >= bar.maximum() - 40

    def _maybe_scroll_to_bottom(self):
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))
