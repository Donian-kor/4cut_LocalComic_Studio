import copy
import json
from pathlib import Path


class WorkflowAdapter:
    def __init__(self, path, base_dir=None, profile=None):
        p = Path(path)
        if not p.is_absolute() and base_dir:
            p = Path(base_dir) / p
        self.path = p
        self.profile = profile

    def load(self):
        if not self.path.exists():
            raise FileNotFoundError(f"ComfyUI workflow 파일이 없습니다: {self.path}")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("ComfyUI API workflow JSON이 객체가 아닙니다.")
        return data

    def prepare(self, prompt, seed, width=None, height=None):
        wf = copy.deepcopy(self.load())
        profile = self.profile
        width = int(width or getattr(profile, "width", 768))
        height = int(height or getattr(profile, "height", 768))

        text_nodes = self._find_nodes(wf, "CLIPTextEncode")
        if not text_nodes:
            raise ValueError("workflow에서 CLIPTextEncode 노드를 찾을 수 없습니다.")
        positive_id, negative_id = self._select_prompt_nodes(text_nodes)
        wf[positive_id].setdefault("inputs", {})["text"] = prompt
        if negative_id:
            wf[negative_id].setdefault("inputs", {})["text"] = getattr(profile, "negative_prompt", "")

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

        return wf

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
    def _select_prompt_nodes(nodes):
        ids = list(nodes.keys())
        positive = ids[0]
        negative = ids[1] if len(ids) > 1 else None
        return positive, negative
