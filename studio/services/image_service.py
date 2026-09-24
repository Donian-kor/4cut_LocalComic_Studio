import logging
from pathlib import Path

from PIL import Image, ImageDraw

from studio.services.bubble import find_font
from studio.services.bubble_detector import BubbleDetector

_FONT_CACHE = {}
logger = logging.getLogger(__name__)


def _get_font(size, font_path=None):
    """테스트에서 monkeypatch해도 항상 이 모듈 기준으로 폰트를 얻는다.

    (폰트 경로, 크기)를 키로 사용해 설정 변경 시 새 폰트를 다시 로딩한다.
    """
    size = int(size)
    key = (str(font_path or ""), size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = find_font(size, font_path)
    return _FONT_CACHE[key]


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
    def __init__(self, comfy_client, workflow_adapter, width=512, height=512, detector=None):
        self.comfy = comfy_client
        self.workflow = workflow_adapter
        self.width = width
        self.height = height
        self.detector = detector or BubbleDetector()
        # 설정된 폰트 경로를 대사 폰트 피팅에도 동일하게 사용한다.
        self.font_path = str(getattr(workflow_adapter, "font_path", "") or "")

    def generate_panel(self, panel, output_dir, cancel_check=None, style_prompt=""):
        prompt = str(getattr(panel, "image_prompt", "") or "")
        revision_prompt = str(getattr(panel, "revision_prompt", "") or "").strip()
        if revision_prompt:
            prompt = f"{prompt}. Additional requested change: {revision_prompt}"
        workflow = self.workflow.prepare(
            prompt, panel.seed, self.width, self.height,
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

    def apply_dialogue(self, panel, font_name=None, font_size=None, cancel_check=None):
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

        # 2. 실제 말풍선 크기(85% 가용 영역)에 맞게 폰트 크기 및 개행 자동 피팅 (Auto-Fit)
        text, final_font_size = self._fit_dialogue_text(
            dialogue,
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
        logger.info(
            "패널 %s 대사 합성 완료 (폰트 %spx, 오프셋: %s,%s) -> %s",
            panel.index, final_font_size, offset_x, offset_y, dialogued_path.name,
        )
        return panel.image_path

    def _fit_dialogue_text(self, dialogue, target_width=None, target_height=None):
        """말풍선 크기(너비, 높이)의 85% 영역(15% 여백)에 가장 꽉 차는 최적 폰트 크기를 이분 탐색으로 계산한다."""
        target_w = target_width or (self.width * 0.6)
        target_h = target_height or (self.height * 0.25)

        # 15% 여백 적용 (가로 85%, 세로 85% 가용 상자)
        safe_w = max(80, int(target_w * 0.85))
        safe_h = max(50, int(target_h * 0.85))

        dummy = ImageDraw.Draw(Image.new("RGB", (8, 8)))

        # 이분 탐색 (Binary Search: 14px ~ 110px)
        low, high = 14, 110
        best_size = 14
        best_lines = [dialogue]

        while low <= high:
            mid = (low + high) // 2
            font = _get_font(mid, self.font_path)
            lines = _wrap_cjk(dialogue, safe_w, font)

            # 전체 텍스트 블록의 가로/세로 바운딩 박스 계산
            line_widths = []
            for line in lines:
                if not line:
                    continue
                bbox = dummy.textbbox((0, 0), line, font=font)
                line_widths.append(bbox[2] - bbox[0])

            max_line_w = max(line_widths) if line_widths else 0
            sample_bbox = dummy.textbbox((0, 0), "가Ag", font=font)
            single_line_h = max(16, sample_bbox[3] - sample_bbox[1])
            line_spacing = max(4, int(mid * 0.2))
            total_block_h = len(lines) * single_line_h + max(0, len(lines) - 1) * line_spacing

            # 가용 상자(85%) 수용 여부 판별
            if max_line_w <= safe_w and total_block_h <= safe_h:
                best_size = mid
                best_lines = lines
                low = mid + 1  # 더 큰 폰트 크기 시도
            else:
                high = mid - 1  # 폰트 크기 축소

        return "\n".join(best_lines), best_size
