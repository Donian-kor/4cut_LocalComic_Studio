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

    # 그림체(아트 스타일) 프리셋.
    # 사용자에게는 간단한 이름만 노출하고, 내부에서 ComfyUI용 상세 프롬프트로 변환한다.
    ART_STYLE_PRESETS = {
    "캐주얼 만화": (
        "casual comic illustration, cute and relaxed visual style, "
        "clean lineart, bright cheerful colors, "
        "expressive facial expressions, simple shapes, "
        "soft cel shading, friendly and playful appearance"
    ),

    "웹툰": (
        "modern Korean webtoon illustration style, "
        "clean crisp lineart, polished character design, "
        "natural vibrant colors, smooth cel shading, "
        "expressive facial features, soft cinematic lighting, "
        "clean polished digital artwork"
    ),

    "SD / 치비": (
        "super deformed chibi illustration style, "
        "cute characters with large heads and small bodies, "
        "rounded shapes, clean bold outlines, "
        "bright cheerful colors, simple shading, "
        "highly expressive cute facial expressions"
    ),

    "일본 만화": (
        "Japanese manga illustration style, "
        "distinctive manga character design, clean bold linework, "
        "expressive eyes and facial expressions, "
        "dynamic character poses, traditional manga shading, "
        "screentone texture, detailed black and white or limited-color artwork"
    ),

    "수채화": (
        "watercolor illustration style, "
        "soft translucent colors, gentle color bleeding, "
        "delicate brushstrokes, natural paper texture, "
        "warm atmospheric colors, subtle shading, "
        "hand-painted organic appearance"
    ),

    "연필 스케치": (
        "pencil sketch illustration style, "
        "hand-drawn graphite lines, visible pencil strokes, "
        "natural rough sketch texture, monochrome or low-saturation tones, "
        "soft graphite shading, imperfect handmade appearance"
    ),

    "잉크 만화": (
        "traditional ink illustration style, "
        "strong confident pen lines, bold black outlines, "
        "high contrast black and white artwork, "
        "expressive linework, cross-hatching, halftone shading, "
        "classic hand-inked appearance"
    ),

    "레트로 만화": (
        "retro comic illustration style, "
        "limited vintage color palette, bold outlines, "
        "slightly faded colors, vintage printing texture, "
        "subtle paper grain, classic old comic book appearance"
    ),
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
        # 분위기 드롭다운 초기화
        self._sync_style_items()
        self._load_style()
        self.form.styleEdit.currentTextChanged.connect(self._on_style_changed)
        # 그림체 드롭다운 초기화
        self._sync_art_style_items()
        self._load_art_style()
        self.form.artStyleEdit.currentTextChanged.connect(self._on_art_style_changed)

    # ── 분위기 (장르) ──────────────────────────────────

    def _sync_style_items(self):
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

    # ── 그림체 (아트 스타일) ───────────────────────────

    def _sync_art_style_items(self):
        current = self.form.artStyleEdit.currentText()
        if self.form.artStyleEdit.count() == 0:
            self.form.artStyleEdit.addItems(list(self.ART_STYLE_PRESETS.keys()))
        if current:
            self.form.artStyleEdit.setCurrentText(current)

    def _load_art_style(self):
        if self.settings_manager is None:
            return
        try:
            saved = str(self.settings_manager.section("general").get("art_style_prompt", ""))
            for label, prompt in self.ART_STYLE_PRESETS.items():
                if saved.lower() == prompt.lower():
                    self.form.artStyleEdit.setCurrentText(label)
                    return
            # 저장된 값이 프리셋에 없으면 기본(캐주얼 만화) 선택
            self.form.artStyleEdit.setCurrentText("캐주얼 만화")
        except Exception:
            self.form.artStyleEdit.setCurrentText("캐주얼 만화")

    def _on_art_style_changed(self, label):
        if self.settings_manager is None:
            return
        prompt = self.ART_STYLE_PRESETS.get(label, "")
        try:
            self.settings_manager.section("general")["art_style_prompt"] = prompt
            self.settings_manager.save()
        except Exception:
            pass

    # ── 공통 ──────────────────────────────────────────

    def _emit(self):
        idea = self.form.ideaEdit.toPlainText().strip()
        if not idea:
            self.form.ideaEdit.setFocus()
            return

        # 분위기(장르) 프롬프트
        mood_label = self.form.styleEdit.currentText().strip() or "자동"
        mood = self.STYLE_PRESETS.get(mood_label, "")

        # 그림체(아트 스타일) 프롬프트
        art_label = self.form.artStyleEdit.currentText().strip()
        art_prompt = self.ART_STYLE_PRESETS.get(art_label, "")

        # 우선순위: 그림체 > 분위기.
        # 그림체가 시각적 렌더링에 더 직접적이므로 앞쪽에 배치한다.
        parts = [p for p in (art_prompt, mood) if p]
        combined_style = ", ".join(parts)

        self.generateRequested.emit(idea, combined_style)

    def set_enabled(self, enabled):
        self.form.generateButton.setEnabled(enabled)
        self.form.ideaEdit.setEnabled(enabled)
        self.form.styleEdit.setEnabled(enabled)
        self.form.artStyleEdit.setEnabled(enabled)
