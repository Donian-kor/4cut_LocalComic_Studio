from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
import uuid


def _now():
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class ChatMessageData:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    role: str = "ai"
    kind: str = "text"
    text: str = ""
    created_at: str = field(default_factory=_now)
    mood: str = ""
    art_style: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "kind": self.kind,
            "text": self.text,
            "created_at": self.created_at,
            "mood": self.mood,
            "art_style": self.art_style,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, raw):
        return cls(
            id=str(raw.get("id") or uuid.uuid4().hex[:12]),
            role=str(raw.get("role", "ai")),
            kind=str(raw.get("kind", "text")),
            text=str(raw.get("text", "")),
            created_at=str(raw.get("created_at", _now())),
            mood=str(raw.get("mood", "")),
            art_style=str(raw.get("art_style", "")),
            metadata=dict(raw.get("metadata") or {}),
        )


@dataclass
class ChatSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    title: str = "새 대화"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    messages: List[ChatMessageData] = field(default_factory=list)
    idea: str = ""
    mood: str = "자동"
    art_style: str = "캐주얼 만화"
    status: str = "idle"
    error_message: str = ""
    result_path: str = ""
    panel_paths: List[str] = field(default_factory=list)
    # 한 만화 생성에서 확정된 생성 컨텍스트. 하드코딩하지 않고 세션별로 보존한다.
    master_seed: int = 0
    character_prompt: str = ""
    style_prompt: str = ""
    generation_config: Dict[str, Any] = field(default_factory=dict)
    comic_data: Dict[str, Any] = field(default_factory=dict)
    comic: Any = None  # runtime-only convenience; never serialized directly

    def touch(self):
        self.updated_at = _now()

    def add_message(self, message):
        self.messages.append(message)
        self.touch()

    def set_title_from_idea(self, idea):
        clean = " ".join(str(idea).strip().split())
        if not clean:
            return
        self.title = clean[:40].rstrip() + ("…" if len(clean) > 40 else "")
        self.touch()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
            "idea": self.idea,
            "mood": self.mood,
            "art_style": self.art_style,
            "status": self.status,
            "error_message": self.error_message,
            "result_path": self.result_path,
            "panel_paths": list(self.panel_paths),
            "master_seed": int(self.master_seed or 0),
            "character_prompt": self.character_prompt,
            "style_prompt": self.style_prompt,
            "generation_config": dict(self.generation_config),
            "comic_data": dict(self.comic_data),
        }

    @classmethod
    def from_dict(cls, raw):
        session = cls(
            id=str(raw.get("id") or uuid.uuid4().hex[:16]),
            title=str(raw.get("title") or "새 대화"),
            created_at=str(raw.get("created_at") or _now()),
            updated_at=str(raw.get("updated_at") or _now()),
            idea=str(raw.get("idea") or ""),
            mood=str(raw.get("mood") or "자동"),
            art_style=str(raw.get("art_style") or "캐주얼 만화"),
            status=str(raw.get("status") or "idle"),
            error_message=str(raw.get("error_message") or ""),
            result_path=str(raw.get("result_path") or ""),
            panel_paths=[str(x) for x in (raw.get("panel_paths") or [])],
            master_seed=int(raw.get("master_seed") or 0),
            character_prompt=str(raw.get("character_prompt") or ""),
            style_prompt=str(raw.get("style_prompt") or ""),
            generation_config=dict(raw.get("generation_config") or {}),
            comic_data=dict(raw.get("comic_data") or {}),
        )
        session.messages = [ChatMessageData.from_dict(x) for x in (raw.get("messages") or []) if isinstance(x, dict)]
        return session
