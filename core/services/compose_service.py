from pathlib import Path
from PIL import Image, ImageDraw
from compose.layout import make_2x2
from compose.bubble import draw_dialogue, find_font


class ComposeService:
    """말풍선 없는 컷 위에 PIL로 말풍선+대사를 고정 위치에 그린다.

    생성 이미지에 말풍선이 없으므로, ComfyUI 내부에서 대사 위치를
    AI로 맞출 필요가 없다. 항상 같은 상단 위치에 같은 크기로 그려
    대사가 말풍선을 벗어나지 않는다.
    """

    def __init__(self, font_size=28):
        self.font_size = font_size

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
                    draw = ImageDraw.Draw(panel)
                    w, h = panel.size
                    font = find_font(int(self.font_size))
                    draw_dialogue(
                        draw,
                        (18, 18, w - 18, int(h * 0.24)),
                        p.dialogue,
                        font,
                    )
                with_images.append(panel)
        canvas = make_2x2(with_images)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path)
        comic.output_path = str(output_path)
        return str(output_path)
