from pathlib import Path
from PySide6.QtCore import Signal, QTimer, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtGui import QPixmap

from ui import theme


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

        # 실시간 카운트업 타이머 설정
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_timer_tick)
        self.elapsed_seconds = 0

        # 카드 슬롯 위젯 매핑
        self.slots = [
            (self.form.slotCard1, self.form.slotImg1, self.form.slotTxt1),
            (self.form.slotCard2, self.form.slotImg2, self.form.slotTxt2),
            (self.form.slotCard3, self.form.slotImg3, self.form.slotTxt3),
            (self.form.slotCard4, self.form.slotImg4, self.form.slotTxt4),
        ]
        self._apply_base_styles()
        self.reset_ui()

    def _apply_base_styles(self):
        # 다크 테마 기본 카드 스타일시트 적용
        for card, img, txt in self.slots:
            card.setStyleSheet(theme.render("""
                QFrame {
                    background-color: $SURFACE_RAISED;
                    border: 1px solid $BORDER;
                    border-radius: 10px;
                }
            """))
            img.setStyleSheet(theme.render("background: transparent; color: $TEXT_FAINT; font-size: 24px;"))
            txt.setStyleSheet(theme.render("background: transparent; color: $TEXT_DIM; font-size: 12px; font-weight: 500;"))

    def reset_ui(self):
        """생성 시작 시 모든 UI와 타이머, 슬롯 카드를 대기 상태로 초기화한다."""
        self.elapsed_seconds = 0
        self.form.timerLabel.setText("⏱️ 진행 시간 00:00")
        self.form.timerLabel.setStyleSheet(theme.render("color: $ACCENT_TEXT; font-weight: bold; font-size: 14px; font-family: $MONO_STACK;"))
        self.form.titleLabel.setText("AI가 4컷 만화를 만들고 있어요")
        self.form.titleLabel.setStyleSheet(theme.render("color: $TEXT; font-size: 18px; font-weight: bold;"))
        self.form.statusLabel.setText("생성을 준비하는 중...")
        self.form.statusLabel.setStyleSheet(theme.render("color: $TEXT_MUTED; font-size: 14px;"))
        self.form.progressBar.setMaximum(4)
        self.form.progressBar.setValue(0)
        self.form.stepLabel.setText("① 스토리 구상  ➜  ② 컷별 생성  ➜  ③ 대사 합성  ➜  ④ 4컷 완성")
        self.form.stepLabel.setStyleSheet(theme.render("color: $TEXT_DIM; font-size: 12px;"))

        for idx, (card, img, txt) in enumerate(self.slots, start=1):
            card.setStyleSheet(theme.render("""
                QFrame {
                    background-color: $SURFACE_RAISED;
                    border: 1px solid $BORDER;
                    border-radius: 10px;
                }
            """))
            img.clear()
            img.setText("⏳")
            img.setStyleSheet(theme.render("background: transparent; color: $TEXT_FAINT; font-size: 24px;"))
            txt.setText(f"{idx}컷 대기 중")
            txt.setStyleSheet(theme.render("background: transparent; color: $TEXT_DIM; font-size: 12px;"))

    def start_timer(self):
        self.elapsed_seconds = 0
        self.timer.start()

    def stop_timer(self):
        self.timer.stop()

    def _on_timer_tick(self):
        self.elapsed_seconds += 1
        mins = self.elapsed_seconds // 60
        secs = self.elapsed_seconds % 60
        self.form.timerLabel.setText(f"⏱️ 진행 시간 {mins:02d}:{secs:02d}")

    def set_generating(self, generating):
        self.form.cancelButton.setEnabled(generating)
        if generating:
            self.reset_ui()
            self.start_timer()
        else:
            self.stop_timer()

    def set_status(self, message, current, total):
        """서버 진행 상태에 따라 슬롯 강조, 프로그레스바, 스마트 체크리스트를 갱신한다."""
        self.form.statusLabel.setText(message)
        self.form.progressBar.setMaximum(max(1, total))
        self.form.progressBar.setValue(max(0, min(current, total)))

        # 스마트 체크리스트 및 컷 슬롯 하이라이트
        if current <= 0:
            self.form.stepLabel.setText("<b>① 스토리 구상 (LM Studio)</b>  ➜  ② 컷별 생성  ➜  ③ 대사 합성  ➜  ④ 4컷 완성")
        elif current < total:
            self.form.stepLabel.setText(f"① 스토리 완료  ➜  <b>② 컷별 생성 ({current + 1}/4컷 중)</b>  ➜  ③ 대사 합성  ➜  ④ 4컷 완성")
            self.highlight_active_slot(current + 1)
        else:
            self.form.stepLabel.setText("① 스토리 완료  ➜  ② 컷 생성 완료  ➜  ③ 대사 합성 완료  ➜  <b>④ 4컷 완성 중</b>")

    def highlight_active_slot(self, panel_index):
        """현재 생성 중인 컷 카드를 강조 표시한다."""
        if 1 <= panel_index <= 4:
            card, img, txt = self.slots[panel_index - 1]
            card.setStyleSheet(theme.render("""
                QFrame {
                    background-color: $SURFACE_HOVER;
                    border: 2px solid $ACCENT;
                    border-radius: 10px;
                }
            """))
            txt.setText(f"🔄 {panel_index}컷 생성 중...")
            txt.setStyleSheet(theme.render("background: transparent; color: $ACCENT_SOFT_TEXT; font-size: 12px; font-weight: bold;"))

    def set_panel_thumbnail(self, panel_index, image_path):
        """완료된 컷의 썸네일을 해당 슬롯 카드에 즉시 노출한다."""
        if not (1 <= panel_index <= 4):
            return
        card, img, txt = self.slots[panel_index - 1]
        card.setStyleSheet(theme.render("""
            QFrame {
                background-color: $SUCCESS_SOFT;
                border: 2px solid $SUCCESS;
                border-radius: 10px;
            }
        """))
        if image_path and Path(image_path).exists():
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                img.setPixmap(scaled)
        txt.setText(f"✓ {panel_index}컷 완료")
        txt.setStyleSheet(theme.render("background: transparent; color: $SUCCESS_TEXT; font-size: 12px; font-weight: bold;"))

    def set_failed(self, message):
        """생성 실패 시 타이머를 멈추고 붉은색 오류 테마와 실패 메시지를 노출한다."""
        self.stop_timer()
        self.form.titleLabel.setText("⚠️ 생성 중 오류가 발생했습니다")
        self.form.titleLabel.setStyleSheet(theme.render("color: $DANGER_TEXT; font-size: 18px; font-weight: bold;"))
        self.form.statusLabel.setText(f"오류 내용: {message}\n(설정에서 LM Studio 및 ComfyUI 연결을 확인해 주세요)")
        self.form.statusLabel.setStyleSheet(theme.render("color: $DANGER_TEXT; font-size: 13px; padding: 4px;"))
        self.form.stepLabel.setText("❌ 생성이 중단되었습니다. 설정 확인 후 다시 시도해 주세요.")
        self.form.stepLabel.setStyleSheet(theme.render("color: $DANGER; font-size: 12px;"))

    def set_cancelled(self):
        """생성 취소 시 상태 변경"""
        self.stop_timer()
        self.form.titleLabel.setText("생성이 취소되었습니다")
        self.form.titleLabel.setStyleSheet(theme.render("color: $WARNING; font-size: 18px; font-weight: bold;"))
        self.form.statusLabel.setText("사용자 요청으로 생성을 중단했습니다.")
        self.form.statusLabel.setStyleSheet(theme.render("color: $WARNING_TEXT; font-size: 13px;"))
