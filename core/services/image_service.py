from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from compose.bubble import find_font
from core.services.bubble_detector import BubbleDetector

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
    def __init__(self, comfy_client, workflow_adapter, width=768, height=768, detector=None):
        self.comfy = comfy_client
        self.workflow = workflow_adapter
        self.width = width
        self.height = height
        self.detector = detector or BubbleDetector()

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
        """2단계: 생성된 컷의 말풍선을 YOLO로 감지해 적절한 위치에 대사를 합성한다."""
        dialogue = str(getattr(panel, "dialogue", "") or "").strip()
        if not dialogue or not panel.image_path:
            return panel.image_path

        # 1. YOLO 말풍선 탐지 (미검출 시 안전 기본 오프셋 자동 계산)
        bubble_target = self.detector.get_best_bubble_target(
            panel.image_path,
            img_width=self.width,
            img_height=self.height,
        )

        offset_x = bubble_target["offset_x"]
        offset_y = bubble_target["offset_y"]
        target_w = bubble_target.get("bubble_width", int(self.width * 0.6))
        target_h = bubble_target.get("bubble_height", int(self.height * 0.25))

        # 2. 실제 말풍선 영역 너비에 맞게 동적 줄바꿈 및 폰트 크기 조절
        text, final_font_size = self._fit_dialogue_text(
            dialogue,
            font_size,
            target_width=target_w,
            target_height=target_h,
        )

        # 3. ComfyUI 업로드 및 2단계 실행
        image_name = self.comfy.upload_image(panel.image_path)
        workflow = self.workflow.prepare_stage2(
            image_name, text,
            width=self.width, height=self.height,
            font_name=font_name, font_size=final_font_size,
            offset_x=offset_x, offset_y=offset_y,
        )
        prompt_id = self.comfy.queue_prompt(workflow)
        data = self.comfy.wait_for_image(prompt_id, cancel_check=cancel_check)
        if cancel_check and cancel_check():
            raise InterruptedError("대사 합성이 취소되었습니다.")

        # 4. 합성된 이미지 저장 및 상태 플래그 갱신
        path = Path(panel.image_path)
        dialogued_path = path.with_name(f"panel_{panel.index}_dialogue.png")
        dialogued_path.write_bytes(data)
        panel.image_path = str(dialogued_path)
        panel.dialogue_composited = True
        print(f"[ImageService] 패널 {panel.index} 대사 합성 완료 -> {dialogued_path.name}")
        return panel.image_path

    def _fit_dialogue_text(self, dialogue, font_size, target_width=None, target_height=None):
        """실제 말풍선 크기(또는 기본 영역)에 맞게 대사를 줄바꿈하고 폰트 크기를 조정한다."""
        font_size = int(font_size or 32)
        pad = 20
        max_width = max(80, int((target_width or (self.width * 0.55)) - pad * 2))
        max_block = max(60, int((target_height or (self.height * 0.25)) - pad * 2))
        while True:
            font = _get_font(font_size)
            lines = _wrap_cjk(dialogue, max_width, font)
            bbox = ImageDraw.Draw(Image.new("RGB", (8, 8))).textbbox(
                (0, 0), "가Ag", font=font
            )
            line_height = max(24, bbox[3] - bbox[1]) + 6
            if len(lines) * line_height <= max_block or font_size <= 14:
                break
            font_size -= 2
        return "\n".join(lines), font_size
