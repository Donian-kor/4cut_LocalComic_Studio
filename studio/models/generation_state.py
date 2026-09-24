from dataclasses import dataclass, field
from typing import List

@dataclass
class GenerationState:
    phase: str = "idle"
    message: str = ""
    current_panel: int = 0
    total_panels: int = 4
    completed_images: List[str] = field(default_factory=list)
    cancelled: bool = False
    error: str = ""
