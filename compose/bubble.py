import os
from pathlib import Path
from PIL import ImageFont


def find_font(size):
    candidates = [
        os.environ.get("WINDIR", "C:/Windows") + "/Fonts/malgun.ttf",
        os.environ.get("WINDIR", "C:/Windows") + "/Fonts/malgunbd.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                pass
    return ImageFont.load_default()


def _wrap_text(draw, text, font, max_width):
    lines = []
    for paragraph in str(text).splitlines() or [""]:
        current = ""
        for ch in paragraph:
            test = current + ch
            if current and draw.textbbox((0, 0), test, font=font)[2] > max_width:
                lines.append(current)
                current = ch
            else:
                current = test
        lines.append(current)
    return lines


def draw_dialogue(draw, box, text, font=None):
    if not text:
        return
    x1, y1, x2, y2 = box
    if font is None:
        font = find_font(28)
    padding = 14
    max_width = max(80, x2 - x1 - padding * 2)
    lines = _wrap_text(draw, text, font, max_width)
    bbox = draw.textbbox((0, 0), "가Ag", font=font)
    line_h = max(24, bbox[3] - bbox[1])
    needed_h = padding * 2 + line_h * len(lines) + 4 * max(0, len(lines) - 1)
    bottom = min(y2, y1 + needed_h)
    draw.rounded_rectangle((x1, y1, x2, bottom), radius=18, fill="white", outline="black", width=3)
    ty = y1 + padding
    for line in lines:
        draw.text((x1 + padding, ty), line, fill="black", font=font)
        ty += line_h + 4
