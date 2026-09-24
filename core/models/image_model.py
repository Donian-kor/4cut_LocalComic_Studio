from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class ImageModelProfile:
    id: str
    name: str
    model_file: str
    workflow: str
    width: int = 768
    height: int = 768
    steps: int = 28
    cfg: float = 4.0
    sampler: str = "euler_ancestral"
    scheduler: str = "beta"
    negative_prompt: str = "low quality, blurry, deformed, bad anatomy, extra fingers, extra limbs"
    stage2_workflow: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        values = dict(data)
        return cls(
            id=str(values.get("id", "custom")),
            name=str(values.get("name", values.get("id", "Custom Model"))),
            model_file=str(values.get("model_file", "")),
            workflow=str(values.get("workflow", "")),
            stage2_workflow=str(values.get("stage2_workflow", "")),
            width=int(values.get("width", 768)),
            height=int(values.get("height", 768)),
            steps=int(values.get("steps", 28)),
            cfg=float(values.get("cfg", 4.0)),
            sampler=str(values.get("sampler", "euler_ancestral")),
            scheduler=str(values.get("scheduler", "beta")),
            negative_prompt=str(values.get("negative_prompt", "")),
        )
