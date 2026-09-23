import json
import os
import subprocess
from pathlib import Path


class BubbleDetector:
    """ComfyUI 환경의 YOLO 모델을 사용하여 이미지 내 말풍선 Bbox를 감지하는 탐지기."""

    def __init__(self, python_exe=None, model_path=None):
        self.python_exe = python_exe or self._find_comfy_python()
        self.model_path = model_path or self._find_model_path()

    @staticmethod
    def _find_comfy_python():
        local_app = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            Path(local_app) / "Comfy-Desktop/ComfyUI-Installs/donian/ComfyUI/.venv/Scripts/python.exe",
            Path(local_app) / "Comfy-Desktop/ComfyUI-Installs/donian/standalone-env/python.exe",
        ]
        # glob으로 Comfy-Desktop 내 python.exe 탐색
        if local_app:
            base = Path(local_app) / "Comfy-Desktop"
            if base.exists():
                for p in base.glob("**/Scripts/python.exe"):
                    if p not in candidates:
                        candidates.append(p)
        for c in candidates:
            if c and c.exists():
                return str(c)
        return ""

    @staticmethod
    def _find_model_path():
        local_app = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            Path(local_app) / "Comfy-Desktop/ComfyUI-Shared/models/ultralytics/bbox/comic-speech-bubble-detector.pt",
        ]
        if local_app:
            base = Path(local_app) / "Comfy-Desktop"
            if base.exists():
                for p in base.glob("**/comic-speech-bubble-detector.pt"):
                    if p not in candidates:
                        candidates.append(p)
        for c in candidates:
            if c and c.exists():
                return str(c)
        return ""

    def is_available(self):
        return bool(self.python_exe and Path(self.python_exe).exists() and
                    self.model_path and Path(self.model_path).exists())

    def detect(self, image_path, conf=0.25):
        """이미지에서 말풍선 Bbox 목록을 검출한다.

        반환값:
            list of dict: [{"bbox": [x1, y1, x2, y2], "conf": float, "area": int}, ...]
            실패하거나 검출 결과가 없으면 빈 리스트 [] 반환.
        """
        if not self.is_available():
            print("[BubbleDetector] ComfyUI Python 또는 YOLO 모델 경로를 찾을 수 없습니다.")
            return []

        img_path = Path(image_path).resolve()
        if not img_path.exists():
            return []

        # ComfyUI Python 환경에서 1회성 초고속 YOLO 추론 실행.
        # 인자는 -c 뒤 argv로 전달해 경로의 따옴표/특수문자 이슈를 피한다.
        script = (
            "import sys, json\n"
            "from ultralytics import YOLO\n"
            "model = YOLO(sys.argv[1])\n"
            "results = model(sys.argv[2], conf=float(sys.argv[3]), verbose=False)\n"
            "boxes = []\n"
            "for r in results:\n"
            "    for box in r.boxes.data.tolist():\n"
            "        x1, y1, x2, y2, c, cls_id = box[:6]\n"
            "        w, h = max(0, x2 - x1), max(0, y2 - y1)\n"
            "        boxes.append({'bbox': [int(x1), int(y1), int(x2), int(y2)], 'conf': float(c), 'area': int(w * h)})\n"
            "print(json.dumps(boxes))\n"
        )

        try:
            res = subprocess.run(
                [self.python_exe, "-c", script, str(self.model_path), str(img_path), str(float(conf))],
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
            output = res.stdout.strip()
            # 마지막 줄에서 json 파싱
            lines = [line.strip() for line in output.splitlines() if line.strip()]
            if lines:
                return json.loads(lines[-1])
        except Exception as e:
            print(f"[BubbleDetector] YOLO 추론 중 오류 발생: {e}")
        return []

    def get_best_bubble_target(self, image_path, img_width=768, img_height=768, conf=0.25):
        """가장 적합한 말풍선의 중심 오프셋(offset_x, offset_y)과 최대 허용 너비/높이를 반환한다.

        ComfyUI DrawText+ 기준:
        offset_x = center_x - img_width / 2
        offset_y = center_y - img_height / 2

        말풍선이 없거나 검출 실패 시:
        상단 안전 기본 영역(상단 중앙 15~20% 위치)을 기본값으로 반환하여 크래시 방지.
        """
        boxes = self.detect(image_path, conf=conf)
        if boxes:
            # 면적이 가장 크고 신뢰도가 높은 상위 1개 선택
            boxes.sort(key=lambda b: (b.get("area", 0)), reverse=True)
            best = boxes[0]
            x1, y1, x2, y2 = best["bbox"]
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            bw = max(60, x2 - x1)
            bh = max(40, y2 - y1)
            offset_x = int(cx - (img_width / 2))
            offset_y = int(cy - (img_height / 2))
            print(f"[BubbleDetector] 말풍선 검출 성공: Bbox={best['bbox']}, conf={best['conf']:.2f}, offset=({offset_x}, {offset_y})")
            return {
                "detected": True,
                "bbox": [x1, y1, x2, y2],
                "offset_x": offset_x,
                "offset_y": offset_y,
                "bubble_width": bw,
                "bubble_height": bh,
            }

        # 미검출 시 안전 기본 좌표 (화면 상단 중앙)
        default_cx = img_width / 2
        default_cy = img_height * 0.18
        offset_x = int(default_cx - (img_width / 2)) # 0
        offset_y = int(default_cy - (img_height / 2)) # 상단 쪽 오프셋
        print(f"[BubbleDetector] 말풍선 미검출 -> 상단 기본 영역으로 안전 대체 (offset: {offset_x}, {offset_y})")
        return {
            "detected": False,
            "bbox": [int(img_width * 0.1), int(img_height * 0.05), int(img_width * 0.9), int(img_height * 0.3)],
            "offset_x": offset_x,
            "offset_y": offset_y,
            "bubble_width": int(img_width * 0.7),
            "bubble_height": int(img_height * 0.22),
        }

