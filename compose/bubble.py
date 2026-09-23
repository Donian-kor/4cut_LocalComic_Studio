import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def find_font_path(explicit=None):
    candidates = []
    if explicit:
        candidates.append(explicit)
    candidates += [
        os.environ.get("COMFY_FONT_PATH", ""),
        os.environ.get("WINDIR", "C:/Windows") + "/Fonts/malgun.ttf",
        os.environ.get("WINDIR", "C:/Windows") + "/Fonts/malgunbd.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if path and Path(path).exists():
            return str(path).replace("\\", "/")
    return ""


# (폰트 경로, 크기)를 키로 캐시한다. 설정의 폰트 경로/크기가 바뀌면
# 새 키로 재로딩되므로 이전 설정의 폰트가 재사용되지 않는다.
_FONT_CACHE = {}


def find_font(size, font_path=None):
    """설정된 폰트 경로를 우선 사용하고, 없으면 시스템 기본 후보에서 찾는다."""
    key = (str(font_path or "").replace("\\", "/"), int(size))
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached
    font = _load_font(int(size), font_path)
    _FONT_CACHE[key] = font
    return font


def _load_font(size, font_path):
    candidates = []
    if font_path:
        candidates.append(str(font_path))
    candidates += [
        os.environ.get("WINDIR", "C:/Windows") + "/Fonts/malgun.ttf",
        os.environ.get("WINDIR", "C:/Windows") + "/Fonts/malgunbd.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if path and Path(path).exists():
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


def wrap_text(text, max_width, font_size=28, font=None):
    """DrawText+용: 폰트 메트릭스로 대사를 max_width 픽셀 안에서 줄바꿈한다.

    DrawText+ 노드는 자동 줄바꿈이 없어 개행(\\n)을 미리 넣어야 하며,
    각 줄은 노드에서 가로 중앙 정렬된다.
    """
    if not text:
        return ""
    if font is None:
        font = find_font(int(font_size))
    dummy = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    lines = _wrap_text(dummy, str(text), font, max(40, int(max_width)))
    return "\n".join(lines)


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
