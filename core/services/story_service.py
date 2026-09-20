from core.models.comic import Comic, Character, Panel

class StoryService:
    def __init__(self, llm_client):
        self.llm = llm_client

    def create_comic(self, idea, style=""):
        system = '''
You are a 4-panel comic planning assistant.
Return ONLY valid JSON with:
{
  "title": "...",
  "style": "...",
  "character": {"name":"...", "appearance":"...", "personality":"..."},
  "panels": [
    {"scene":"...", "dialogue":"...", "speaker":"...", "image_prompt":"..."},
    {"scene":"...", "dialogue":"...", "speaker":"...", "image_prompt":"..."},
    {"scene":"...", "dialogue":"...", "speaker":"...", "image_prompt":"..."},
    {"scene":"...", "dialogue":"...", "speaker":"...", "image_prompt":"..."}
  ]
}
There must be exactly 4 panels.
Keep the story short, coherent, and visually drawable.
Repeat the same character appearance consistently in every image_prompt.
'''
        user = f"User idea: {idea}\nRequested style: {style or 'auto'}"
        data = self.llm.chat_json(system, user)
        character = data.get("character", {})
        comic = Comic(
            idea=idea,
            title=data.get("title", "4컷 만화"),
            style=data.get("style", style or "comic"),
            character=Character(
                name=character.get("name", "Character"),
                appearance=character.get("appearance", ""),
                personality=character.get("personality", ""),
            ),
        )
        panels = data.get("panels", [])[:4]
        while len(panels) < 4:
            panels.append({"scene":"", "dialogue":"", "speaker":"", "image_prompt":""})
        comic.panels = [
            Panel(i+1, p.get("scene",""), p.get("image_prompt",""), p.get("dialogue",""), p.get("speaker",""), seed=1000+i)
            for i, p in enumerate(panels)
        ]
        # Enforce a common character description in every panel prompt.
        char = comic.character.prompt_description()
        for p in comic.panels:
            p.image_prompt = f"{char}. {p.image_prompt}. 4-panel comic style, consistent character design."
        return comic
