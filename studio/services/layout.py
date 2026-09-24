from PIL import Image

def make_2x2(images):
    if len(images) != 4:
        raise ValueError("Exactly 4 images are required")
    w = max(i.width for i in images)
    h = max(i.height for i in images)
    canvas = Image.new("RGB", (w*2, h*2), "white")
    for idx, img in enumerate(images):
        img = img.convert("RGB")
        # 비율을 유지한 뒤 셀 크기에 맞게 축소하고 가운데에 letterbox로 배치한다.
        scale = min(w / img.width, h / img.height)
        new_w = max(1, int(img.width * scale))
        new_h = max(1, int(img.height * scale))
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        cell = Image.new("RGB", (w, h), "white")
        cell.paste(resized, ((w - new_w) // 2, (h - new_h) // 2))
        canvas.paste(cell, ((idx%2)*w, (idx//2)*h))
    return canvas
