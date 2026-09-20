from PIL import ImageDraw, ImageFont

def draw_dialogue(draw, box, text, font=None):
    if not text:
        return
    x1, y1, x2, y2 = box
    radius = 18
    draw.rounded_rectangle(box, radius=radius, fill="white", outline="black", width=3)
    if font is None:
        font = ImageFont.load_default()
    # Simple text placement; wrapping can be expanded later.
    draw.multiline_text((x1+12, y1+10), text, fill="black", font=font, spacing=4)
