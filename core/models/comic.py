from dataclasses import dataclass, field
from typing import List

@dataclass
class Character:
    name: str = ""
    appearance: str = ""
    personality: str = ""

    def prompt_description(self) -> str:
        return f"{self.name}: {self.appearance}. Personality: {self.personality}."

    def visual_prompt(self) -> str:
        """이번 만화에서 모든 패널이 공유할 캐릭터 시각적 특징."""
        if self.name and self.appearance:
            return f"{self.name}: {self.appearance}"
        return self.appearance or self.name

@dataclass
class Panel:
    index: int
    scene: str = ""
    image_prompt: str = ""
    dialogue: str = ""
    speaker: str = ""
    seed: int = 0
    image_path: str = ""
    dialogue_composited: bool = False
    revision_prompt: str = ""
    revision_count: int = 0

    def to_dict(self):
        return {
            "index": int(self.index),
            "scene": self.scene,
            "image_prompt": self.image_prompt,
            "dialogue": self.dialogue,
            "speaker": self.speaker,
            "seed": int(self.seed or 0),
            "image_path": self.image_path,
            "dialogue_composited": bool(self.dialogue_composited),
            "revision_prompt": self.revision_prompt,
            "revision_count": int(self.revision_count or 0),
        }

    @classmethod
    def from_dict(cls, raw):
        return cls(
            index=int(raw.get("index", 0)),
            scene=str(raw.get("scene") or ""),
            image_prompt=str(raw.get("image_prompt") or ""),
            dialogue=str(raw.get("dialogue") or ""),
            speaker=str(raw.get("speaker") or ""),
            seed=int(raw.get("seed") or 0),
            image_path=str(raw.get("image_path") or ""),
            dialogue_composited=bool(raw.get("dialogue_composited", False)),
            revision_prompt=str(raw.get("revision_prompt") or ""),
            revision_count=int(raw.get("revision_count") or 0),
        )

@dataclass
class Comic:
    idea: str = ""
    title: str = ""
    style: str = ""
    character: Character = field(default_factory=Character)
    panels: List[Panel] = field(default_factory=list)
    output_path: str = ""
    # 한 만화 생성 작업에서 1회 확정해 모든 패널이 공유하는 생성 컨텍스트.
    master_seed: int = 0
    character_prompt: str = ""
    style_prompt: str = ""
    generation_config: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "idea": self.idea,
            "title": self.title,
            "style": self.style,
            "character": {
                "name": self.character.name,
                "appearance": self.character.appearance,
                "personality": self.character.personality,
            },
            "panels": [p.to_dict() for p in self.panels],
            "output_path": self.output_path,
            "master_seed": int(self.master_seed or 0),
            "character_prompt": self.character_prompt,
            "style_prompt": self.style_prompt,
            "generation_config": dict(self.generation_config),
        }

    @classmethod
    def from_dict(cls, raw):
        raw_character = dict(raw.get("character") or {})
        comic = cls(
            idea=str(raw.get("idea") or ""),
            title=str(raw.get("title") or ""),
            style=str(raw.get("style") or ""),
            character=Character(
                name=str(raw_character.get("name") or ""),
                appearance=str(raw_character.get("appearance") or ""),
                personality=str(raw_character.get("personality") or ""),
            ),
            output_path=str(raw.get("output_path") or ""),
            master_seed=int(raw.get("master_seed") or 0),
            character_prompt=str(raw.get("character_prompt") or ""),
            style_prompt=str(raw.get("style_prompt") or ""),
            generation_config=dict(raw.get("generation_config") or {}),
        )
        comic.panels = [
            Panel.from_dict(x) for x in (raw.get("panels") or [])
            if isinstance(x, dict)
        ]
        return comic
