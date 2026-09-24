import logging
from pathlib import Path
from PIL import Image, ImageDraw
from compose.layout import make_2x2
from compose.bubble import draw_dialogue, find_font, wrap_text

logger = logging.getLogger(__name__)


class ComposeService:
    """말풍선 없는 컷 위에 PIL로 말풍선+대사를 고정 위치에 그린다.

    생성 이미지에 말풍선이 없으므로, ComfyUI 내부에서 대사 위치를
    AI로 맞출 필요가 없다. 항상 같은 상단 위치에 같은 크기로 그려
    대사가 말풍선을 벗어나지 않는다.
    """

    def __init__(self, font_size=110, font_path=""):
        self.font_size = int(font_size)
        self.font_path = str(font_path or "")

    def compose(self, comic, output_path):
        for p in comic.panels:
            if not p.image_path or not Path(p.image_path).exists():
                raise RuntimeError(f"패널 {p.index}의 이미지가 존재하지 않습니다: {p.image_path}")
        with_images = []
        for p in comic.panels:
            with Image.open(p.image_path) as img:
                panel = img.convert("RGB")
                # 2단계(ComfyUI 감지 기반)로 대사가 이미 합성된 패널은 건너뛴다.
                if p.dialogue and not getattr(p, "dialogue_composited", False):
                    logger.warning(
                        "패널 %s: 2단계 합성이 되지 않아 Pillow로 대체 합성합니다.", p.index
                    )
                    draw = ImageDraw.Draw(panel)
                    w, h = panel.size
                    bubble_width = w - 36 - 28
                    bubble_height = int(h * 0.24) - 18 - 28
                    safe_width = max(80, int(bubble_width * 0.85))
                    safe_height = max(50, int(bubble_height * 0.85))
                    font = self._fit_fallback_font(p.dialogue, safe_width, safe_height)
                    fitted_text = "\n".join(wrap_text(p.dialogue, safe_width, font=font).splitlines())
                    draw_dialogue(
                        draw,
                        (18, 18, w - 18, int(h * 0.24)),
                        fitted_text,
                        font,
                    )
                    p.dialogue_status = "fallback"
                elif not p.dialogue:
                    p.dialogue_status = "none"
                with_images.append(panel)
        canvas = make_2x2(with_images)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path)
        comic.output_path = str(output_path)
        return str(output_path)

    def _fit_fallback_font(self, dialogue, max_width, max_height):
        """Fit fallback dialogue into the same compact top bubble area."""
        probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        for size in range(max(14, self.font_size), 13, -1):
            font = find_font(size, self.font_path)
            lines = wrap_text(dialogue, max_width, font=font).splitlines() or [""]
            line_height = probe.textbbox((0, 0), "Ag가", font=font)[3]
            if len(lines) * (line_height + 4) - 4 <= max_height and all(
                probe.textbbox((0, 0), line, font=font)[2] <= max_width for line in lines
            ):
                return font
        return find_font(14, self.font_path)
