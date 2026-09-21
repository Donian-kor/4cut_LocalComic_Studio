from dataclasses import dataclass, field
from typing import List

@dataclass
class Character:
    name: str = ""
    appearance: str = ""
    personality: str = ""

    def prompt_description(self) -> str:
        return f"{self.name}: {self.appearance}. Personality: {self.personality}."

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

@dataclass
class Comic:
    idea: str = ""
    title: str = ""
    style: str = ""
    character: Character = field(default_factory=Character)
    panels: List[Panel] = field(default_factory=list)
    output_path: str = ""
