from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from compose.layout import make_2x2
from compose.bubble import draw_dialogue

class ComposeService:
    def compose(self, comic, output_path):
        images = [Image.open(p.image_path).convert("RGB") for p in comic.panels]
        w = max(i.width for i in images)
        h = max(i.height for i in images)
        canvas = make_2x2(images)
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()
        for idx, panel in enumerate(comic.panels):
            x = (idx % 2) * w
            y = (idx // 2) * h
            if panel.dialogue:
                draw_dialogue(draw, (x+20, y+20, x+w-20, y+85), panel.dialogue, font)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path)
        comic.output_path = str(output_path)
        return str(output_path)
