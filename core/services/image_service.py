from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from compose.bubble import find_font

_FONT_CACHE = {}


def _get_font(size):
    """테스트에서 monkeypatch해도 항상 이 모듈 기준으로 폰트를 얻는다."""
    size = int(size)
    if size not in _FONT_CACHE:
        _FONT_CACHE[size] = find_font(size)
    return _FONT_CACHE[size]


def _wrap_cjk(text, max_width, font):
    """폰트 메트릭스 기준으로 text를 max_width 픽셀 안에서 줄바꿈한다."""
    dummy = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    lines = []
    for paragraph in str(text).splitlines() or [""]:
        current = ""
        for ch in paragraph:
            test = current + ch
            if current and dummy.textlength(test, font=font) > max_width:
                lines.append(current)
                current = ch
            else:
                current = test
        lines.append(current)
    return lines


class ImageService:
    def __init__(self, comfy_client, workflow_adapter, width=768, height=768):
        self.comfy = comfy_client
        self.workflow = workflow_adapter
        self.width = width
        self.height = height

    def generate_panel(self, panel, output_dir, cancel_check=None, style_prompt=""):
        workflow = self.workflow.prepare(
            panel.image_prompt, panel.seed, self.width, self.height,
            dialogue=getattr(panel, "dialogue", ""),
            style_prompt=style_prompt,
        )
        prompt_id = self.comfy.queue_prompt(workflow)
        data = self.comfy.wait_for_image(prompt_id, cancel_check=cancel_check)
        if cancel_check and cancel_check():
            raise InterruptedError("이미지 생성이 취소되었습니다.")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"panel_{panel.index}.png"
        path.write_bytes(data)
        panel.image_path = str(path)
        return str(path)

    def apply_dialogue(self, panel, font_name=None, font_size=32, cancel_check=None):
        """2단계: 생성된 컷의 말풍선을 감지해 대사를 합성한다.

        DrawText+는 자동 줄바꿈이 없으므로 Python에서 폰트 메트릭스로
        미리 줄바꿈한 텍스트를 넘긴다. 말풍선이 감지되지 않은 컷은
        ComfyUI 실행 오류가 나므로, 호출자(comic_service)가 원본을 유지한다.
        """
        dialogue = str(getattr(panel, "dialogue", "") or "").strip()
        if not dialogue or not panel.image_path:
            return panel.image_path

        text, font_size = self._fit_dialogue_text(dialogue, font_size)
        image_name = self.comfy.upload_image(panel.image_path)
        workflow = self.workflow.prepare_stage2(
            image_name, text,
            width=self.width, height=self.height,
            font_name=font_name, font_size=font_size,
        )
        prompt_id = self.comfy.queue_prompt(workflow)
        data = self.comfy.wait_for_image(prompt_id, cancel_check=cancel_check)
        if cancel_check and cancel_check():
            raise InterruptedError("대사 합성이 취소되었습니다.")
        # 기존 파일을 덮어쓰지 않고 대사 합성 이미지를 새 파일로 저장한다.
        path = Path(panel.image_path)
        dialogued_path = path.with_name(f"panel_{panel.index}_dialogue.png")
        dialogued_path.write_bytes(data)
        panel.image_path = str(dialogued_path)
        # ComposeService의 PIL 말풍선 이중 합성을 방지한다.
        panel.dialogue_composited = True
        return panel.image_path

    def _fit_dialogue_text(self, dialogue, font_size):
        """말풍선 크기 추정치(너비 55%, 높이 25%)에 맞게 대사를 줄바꿈하고 폰트 크기를 조정한다."""
        font_size = int(font_size or 32)
        max_width = max(80, int(self.width * 0.55))
        max_block = max(60, int(self.height * 0.25))
        while True:
            font = _get_font(font_size)
            lines = _wrap_cjk(dialogue, max_width, font)
            bbox = ImageDraw.Draw(Image.new("RGB", (8, 8))).textbbox(
                (0, 0), "가Ag", font=font
            )
            line_height = max(24, bbox[3] - bbox[1]) + 6
            if len(lines) * line_height <= max_block or font_size <= 12:
                break
            font_size -= 2
        return "\n".join(lines), font_size
