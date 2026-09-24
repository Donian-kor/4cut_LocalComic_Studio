import copy
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkflowAdapter:
    """이미지 생성(1단계) + 말풍선 감지·대사 합성(2단계) 어댑터.

    1단계 워크플로우는 큰 말풍선을 상단 중앙에 그리도록 프롬프트로 유도하고,
    2단계 워크플로우(옵션)는 Impact Pack의 BboxDetectorSEGS로 말풍선을 감지해
    DrawText+로 대사를 말풍선 한가운데 합성한다.
    2단계 워크플로우 파일이 없거나 대사가 비어 있으면 1단계 결과만 반환한다.
    """

    # Z-Image는 괄호 가중치 문법을 일반 텍스트로 처리하므로 자연어로 말풍선을 지시한다.
    BUBBLE_PROMPT = (
        "large empty white speech bubble at the top center with a completely blank interior, "
        "no text, letters, numbers, symbols, or writing, "
        "solid clean white fill inside the speech bubble, clean outlines"
    )

    DEFAULT_NEGATIVE_TAGS = [
        "text", "letters", "watermark",
        "multiple panels", "split screen", "grid layout", "comic strip",
        "manga page", "panel divider", "2x2 grid", "multiple views", "split frame",
        "blank background", "empty background", "plain white background", "pure white background",
        "isolated on white", "white void background"
    ]

    def __init__(self, path, base_dir=None, profile=None, font_path=None, font_size=None, stage2_path=None):
        p = Path(path)
        if not p.is_absolute() and base_dir:
            p = Path(base_dir) / p
        self.path = p
        self.profile = profile
        self.font_path = font_path
        self.font_size = font_size
        # 조립(assembly) 시점에 stage2 파일 존재를 검증해 없으면 None으로 정규화한다.
        # 준비 단계(prepare_stage2)에서 FileNotFoundError가 발생하지 않도록 한다.
        self.stage2_path = None
        if stage2_path:
            s = Path(stage2_path)
            if not s.is_absolute() and base_dir:
                s = Path(base_dir) / s
            if s.exists():
                self.stage2_path = s
            else:
                logger.warning("2단계 workflow 파일 없음 — 대사 합성(stage2) 비활성: %s", s)

    def load(self):
        if not self.path.exists():
            raise FileNotFoundError(f"ComfyUI workflow 파일이 없습니다: {self.path}")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("ComfyUI API workflow JSON이 객체가 아닙니다.")
        return data

    def prepare(self, prompt, seed, width=None, height=None, dialogue=None, style_prompt=""):
        wf = copy.deepcopy(self.load())
        profile = self.profile
        width = int(width or getattr(profile, "width", 768))
        height = int(height or getattr(profile, "height", 768))

        full_prompt = self._styled_prompt(prompt, style_prompt)

        text_nodes = self._find_nodes(wf, "CLIPTextEncode")
        if not text_nodes:
            raise ValueError("workflow에서 CLIPTextEncode 노드를 찾을 수 없습니다.")
        positive_id, negative_id = self._select_prompt_nodes(wf, text_nodes)
        wf[positive_id].setdefault("inputs", {})["text"] = full_prompt
        if negative_id:
            inputs = wf[negative_id].setdefault("inputs", {})
            # 워크플로우가 원래 가진 negative 텍스트를 버리지 않고
            # 프로필·기본 태그를 병합한다. 덮어쓰기는 값이 있을 때만 수행한다.
            merged = [t.strip() for t in str(inputs.get("text", "") or "").split(",") if t.strip()]
            seen = {t.lower() for t in merged}
            base_neg = str(getattr(profile, "negative_prompt", "") or "")
            for token in [t.strip() for t in base_neg.split(",") if t.strip()]:
                if token.lower() not in seen:
                    merged.append(token)
                    seen.add(token.lower())
            # 배경 관련 negative는 장면 프롬프트가 흰/빈 배경을 명시적으로
            # 요구할 때 생략해 사용자 요청과 충돌하지 않도록 한다.
            lower_prompt = full_prompt.lower()
            wants_open_background = any(
                key in lower_prompt
                for key in (
                    "white background", "pure white", "plain white",
                    "blank background", "empty background", "white void",
                )
            )
            background_tags = {
                "blank background", "empty background", "plain white background",
                "pure white background", "isolated on white", "white void background",
            }
            for extra in self.DEFAULT_NEGATIVE_TAGS:
                if extra.lower() in seen:
                    continue
                if wants_open_background and extra.lower() in background_tags:
                    continue
                merged.append(extra)
                seen.add(extra.lower())
            joined = ", ".join(merged)
            if joined:
                inputs["text"] = joined

        # 말풍선 위치/크기 제약을 positive 프롬프트에 추가한다.
        current_positive = str(wf[positive_id].setdefault("inputs", {}).get("text", "") or "")
        bubble_tag = self.BUBBLE_PROMPT
        if bubble_tag.lower() not in current_positive.lower():
            wf[positive_id]["inputs"]["text"] = f"{current_positive}, {bubble_tag}"

        sampler = self._first_node(wf, "KSampler")
        if sampler:
            inputs = sampler.setdefault("inputs", {})
            inputs["seed"] = int(seed)
            if profile:
                inputs["steps"] = int(profile.steps)
                inputs["cfg"] = float(profile.cfg)
                inputs["sampler_name"] = str(profile.sampler)
                inputs["scheduler"] = str(profile.scheduler)

        latent = self._first_node(wf, "EmptyLatentImage")
        if latent:
            inputs = latent.setdefault("inputs", {})
            inputs["width"], inputs["height"] = width, height
            inputs["batch_size"] = 1

        if profile:
            checkpoint_nodes = self._find_nodes(wf, "CheckpointLoaderSimple")
            for node in checkpoint_nodes.values():
                node.setdefault("inputs", {})["ckpt_name"] = profile.model_file

        # ComfyUI에서 대사 합성 안 함. dialogue 인자는 하위 호환용으로만 유지.
        return wf

    def prepare_stage2(self, image_name, dialogue, width=768, height=768, font_name=None, font_size=32, offset_x=0, offset_y=0):
        """2단계 워크플로우: 안전하게 계산된 오프셋 좌표로 DrawText+ 대사를 합성한다."""
        if not self.stage2_path or not self.stage2_path.exists():
            raise FileNotFoundError(f"2단계(대사 합성) workflow 파일이 없습니다: {self.stage2_path}")
        data = json.loads(self.stage2_path.read_text(encoding="utf-8"))
        wf = copy.deepcopy(data)

        load_nodes = self._find_nodes(wf, "LoadImage")
        if not load_nodes:
            raise ValueError("2단계 workflow에서 LoadImage 노드를 찾을 수 없습니다.")
        next(iter(load_nodes.values())).setdefault("inputs", {})["image"] = str(image_name)

        draw_nodes = self._find_nodes(wf, "DrawText+")
        if not draw_nodes:
            raise ValueError("2단계 workflow에서 DrawText+ 노드를 찾을 수 없습니다.")
        draw = next(iter(draw_nodes.values())).setdefault("inputs", {})
        draw["text"] = str(dialogue or "")
        draw["font"] = font_name or "malgun.ttf"
        draw["size"] = int(font_size or 32)
        # 오프셋 직접 주입 (외부에서 전달된 안전 좌표)
        draw["offset_x"] = int(offset_x)
        draw["offset_y"] = int(offset_y)

        # ImpactInt 노드가 있는 레거시 워크플로우와의 하위 호환성 유지
        int_nodes = list(self._find_nodes(wf, "ImpactInt").items())
        if len(int_nodes) >= 2:
            int_nodes[0][1].setdefault("inputs", {})["value"] = int(width)
            int_nodes[1][1].setdefault("inputs", {})["value"] = int(height)

        save_nodes = self._find_nodes(wf, "SaveImage")
        if save_nodes:
            next(iter(save_nodes.values())).setdefault("inputs", {})["filename_prefix"] = "4cut_dialogue"
        return wf

    @staticmethod
    def _styled_prompt(prompt, style_prompt):
        prompt = str(prompt or "").strip()
        style_prompt = str(style_prompt or "").strip()
        if style_prompt and style_prompt.lower() not in prompt.lower():
            prompt = f"{prompt}. Style: {style_prompt}" if prompt else style_prompt
        return prompt

    @staticmethod
    def _next_id(wf):
        nums = [int(k) for k in wf.keys() if str(k).isdigit()]
        return str(max(nums) + 1 if nums else 1)

    @staticmethod
    def _first_node_id(wf, class_type):
        for key, value in wf.items():
            if isinstance(value, dict) and value.get("class_type") == class_type:
                return key
        return None

    @staticmethod
    def _find_nodes(wf, class_type):
        return {
            key: value for key, value in wf.items()
            if isinstance(value, dict) and value.get("class_type") == class_type
        }

    @staticmethod
    def _first_node(wf, class_type):
        nodes = WorkflowAdapter._find_nodes(wf, class_type)
        return next(iter(nodes.values()), None)

    @staticmethod
    def _select_prompt_nodes(wf, nodes):
        """KSampler 노드의 positive/negative 연결을 먼저 추적하고, 없을 경우 노드 ID 순서로 결정한다."""
        sampler = WorkflowAdapter._first_node(wf, "KSampler")
        if sampler:
            inputs = sampler.get("inputs", {})
            pos_ref = inputs.get("positive")
            neg_ref = inputs.get("negative")
            pos_id = str(pos_ref[0]) if isinstance(pos_ref, list) and len(pos_ref) > 0 else None
            neg_id = str(neg_ref[0]) if isinstance(neg_ref, list) and len(neg_ref) > 0 else None

            if pos_id and pos_id in nodes:
                positive = pos_id
                negative = neg_id if neg_id and neg_id in nodes else None
                return positive, negative

        ids = list(nodes.keys())
        positive = ids[0]
        negative = ids[1] if len(ids) > 1 else None
        return positive, negative
