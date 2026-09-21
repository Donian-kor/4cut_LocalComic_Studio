import random
from core.models.comic import Comic, Character, Panel


class StoryService:
    def __init__(self, llm_client):
        self.llm = llm_client

    def create_comic(self, idea, style=""):
        if not idea.strip():
            raise ValueError("아이디어를 입력해 주세요.")
        system = '''
You are a 4-panel comic planning assistant.
Return ONLY valid JSON with exactly this structure:
{
  "title": "...",
  "style": "...",
  "character": {"name":"...","appearance":"...","personality":"..."},
  "panels": [
    {"scene":"...", "dialogue":"...", "speaker":"...", "image_prompt":"..."},
    {"scene":"...", "dialogue":"...", "speaker":"...", "image_prompt":"..."},
    {"scene":"...", "dialogue":"...", "speaker":"...", "image_prompt":"..."},
    {"scene":"...", "dialogue":"...", "speaker":"...", "image_prompt":"..."}
  ]
}
There must be exactly 4 panels. Every panel must have a non-empty image_prompt.
Keep the story short, coherent, humorous or emotionally clear, and visually drawable.
Repeat the same character appearance consistently in every image_prompt.
'''
        user = f"User idea: {idea.strip()}\nRequested style: {style.strip() or 'auto'}"
        data = self.llm.chat_json(system, user)
        if not self._valid(data):
            repair = system + "\nIMPORTANT: Your previous response was invalid. Return exactly four complete panels with no omissions."
            data = self.llm.chat_json(repair, user)
        if not self._valid(data):
            raise ValueError("LM Studio가 완전한 4컷 만화 JSON을 생성하지 못했습니다. 모델의 JSON 출력 설정을 확인해 주세요.")

        character = data["character"]
        comic = Comic(
            idea=idea.strip(),
            title=str(data.get("title") or "4컷 만화"),
            style=str(data.get("style") or style or "comic"),
            character=Character(
                name=str(character.get("name") or "Character"),
                appearance=str(character.get("appearance") or ""),
                personality=str(character.get("personality") or ""),
            ),
        )
        for i, p in enumerate(data["panels"]):
            comic.panels.append(Panel(
                i + 1,
                str(p.get("scene") or ""),
                str(p.get("image_prompt") or ""),
                str(p.get("dialogue") or ""),
                str(p.get("speaker") or ""),
                seed=random.randint(0, 2**32 - 1),
            ))

        char = comic.character.prompt_description()
        style_text = comic.style
        for p in comic.panels:
            p.image_prompt = (
                f"{char}. Scene: {p.image_prompt}. Style: {style_text}. "
                "4-panel comic illustration, consistent character design, clear composition."
            )
        return comic

    @staticmethod
    def _valid(data):
        if not isinstance(data, dict):
            return False
        character = data.get("character")
        panels = data.get("panels")
        if not isinstance(character, dict) or not character.get("appearance"):
            return False
        if not isinstance(panels, list) or len(panels) != 4:
            return False
        return all(isinstance(p, dict) and str(p.get("image_prompt") or "").strip() for p in panels)
