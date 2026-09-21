import copy
import json
from pathlib import Path


class WorkflowAdapter:
    def __init__(self, path, base_dir=None):
        p = Path(path)
        if not p.is_absolute() and base_dir:
            p = Path(base_dir) / p
        self.path = p

    def load(self):
        if not self.path.exists():
            raise FileNotFoundError(f"ComfyUI workflow 파일이 없습니다: {self.path}")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("ComfyUI workflow JSON이 객체가 아닙니다.")
        return data

    def prepare(self, prompt, seed, width, height):
        wf = copy.deepcopy(self.load())
        positive = self._find_nodes(wf, "CLIPTextEncode")
        if not positive:
            raise ValueError("workflow에서 CLIPTextEncode 노드를 찾을 수 없습니다.")
        # Starter workflow uses node 1; otherwise use the first text encoder.
        positive_id = "1" if "1" in positive else next(iter(positive))
        wf[positive_id].setdefault("inputs", {})["text"] = prompt

        if "2" in wf and isinstance(wf["2"], dict):
            wf["2"].setdefault("inputs", {})["seed"] = int(seed)
        else:
            for node in wf.values():
                if isinstance(node, dict) and node.get("class_type") == "KSampler":
                    node.setdefault("inputs", {})["seed"] = int(seed)
                    break

        if "6" in wf and isinstance(wf["6"], dict):
            inputs = wf["6"].setdefault("inputs", {})
            inputs["width"], inputs["height"] = int(width), int(height)
        else:
            for node in wf.values():
                if isinstance(node, dict) and node.get("class_type") == "EmptyLatentImage":
                    inputs = node.setdefault("inputs", {})
                    inputs["width"], inputs["height"] = int(width), int(height)
                    break
        return wf

    @staticmethod
    def _find_nodes(wf, class_type):
        return {
            key: value for key, value in wf.items()
            if isinstance(value, dict) and value.get("class_type") == class_type
        }
