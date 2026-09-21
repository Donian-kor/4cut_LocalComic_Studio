from pathlib import Path
from PIL import Image, ImageDraw
from compose.layout import make_2x2
from compose.bubble import draw_dialogue, find_font


class ComposeService:
    def compose(self, comic, output_path):
        for p in comic.panels:
            if not p.image_path or not Path(p.image_path).exists():
                raise RuntimeError(f"패널 {p.index}의 이미지가 존재하지 않습니다: {p.image_path}")
        with_images = []
        for p in comic.panels:
            with Image.open(p.image_path) as img:
                with_images.append(img.convert("RGB"))
        w = max(i.width for i in with_images)
        h = max(i.height for i in with_images)
        canvas = make_2x2(with_images)
        draw = ImageDraw.Draw(canvas)
        font = find_font(max(20, min(34, w // 28)))
        for idx, panel in enumerate(comic.panels):
            x = (idx % 2) * w
            y = (idx // 2) * h
            if panel.dialogue:
                draw_dialogue(draw, (x + 18, y + 18, x + w - 18, y + int(h * 0.22)), panel.dialogue, font)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path)
        comic.output_path = str(output_path)
        return str(output_path)
