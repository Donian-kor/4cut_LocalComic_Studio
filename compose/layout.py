from PIL import Image

def make_2x2(images):
    if len(images) != 4:
        raise ValueError("Exactly 4 images are required")
    w = max(i.width for i in images)
    h = max(i.height for i in images)
    canvas = Image.new("RGB", (w*2, h*2), "white")
    for idx, img in enumerate(images):
        canvas.paste(img.convert("RGB").resize((w,h)), ((idx%2)*w, (idx//2)*h))
    return canvas
