import random
import re
from studio.models.comic import Comic, Character, Panel


# ComfyUI(SD 계열) positive prompt에 들어가면 "한 이미지 안에
# 여러 컷을 그려버리는" 다컷 유발 키워드 목록.
_MULTI_PANEL_PATTERNS = (
    r"4[\s\-_]*panel(?:s)?",
    r"four[\s\-_]*panel(?:s)?",
    r"2\s*[x×]\s*2\s*(?:grid|panel|layout|comic)?",
    r"multi[\s\-_]*panel",
    r"comic[\s\-_]*strip",
    r"comic[\s\-_]*page",
    r"4[\s\-_]*cut",
    r"4[\s\-_]*컷",
    r"네[\s\-_]*컷",
    r"사[\s\-_]*컷",
    r"컷[\s\-_]*만화",
    r"컷[\s\-_]*구성",
    r"분할[\s\-_]*컷",
    r"여러[\s\-_]*컷",
)
_MULTI_PANEL_RE = re.compile("|".join(f"(?:{p})" for p in _MULTI_PANEL_PATTERNS), re.IGNORECASE)


def clean_panel_text(text):
    """다컷 유발 키워드를 제거하고 남은 텍스트를 정제한다.

    공백이 무너지지 않게 치환 후 압축하며, 문장부호가 남으면 유지한다.
    """
    cleaned = _MULTI_PANEL_RE.sub(" ", str(text or ""))
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
    return cleaned


class StoryService:
    def __init__(self, llm_client):
        self.llm = llm_client

    def create_comic(self, idea, style="", cancel_check=None, character_prompt=None):
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
Every image_prompt must describe ONE SINGLE STATIC SCENE only (one subject, one moment, single camera angle).
Do NOT describe sequential actions ("first X then Y"), multi-angle shots, split frames, or storyboard layouts in image_prompt.
Keep the story short, coherent, humorous or emotionally clear, and visually drawable.
Repeat the same character appearance consistently in every image_prompt.
Every image_prompt MUST explicitly preserve a visible background/environment appropriate to that panel scene. Do not omit the environment, replace it with an empty backdrop, or use a blank/pure-white background unless the scene explicitly requires it. Background detail may be simple; it only needs to clearly establish the scene/location.
CRITICAL: Every "dialogue" value and every "speaker" value MUST be written entirely in Korean (한국어). Do not use English or any other language for dialogue or speaker. The "image_prompt" may use English for visual clarity.
'''
        user = f"User idea: {idea.strip()}\nRequested style: {style.strip() or 'auto'}"
        data = self.llm.chat_json(system, user, cancel_check=cancel_check)
        if not self._valid(data):
            repair = system + "\nIMPORTANT: Your previous response was invalid. Return exactly four complete panels with no omissions."
            data = self.llm.chat_json(repair, user, cancel_check=cancel_check)
        if not self._valid(data):
            raise ValueError("LM Studio가 완전한 4컷 만화 JSON을 생성하지 못했습니다. 모델의 JSON 출력 설정을 확인해 주세요.")

        character = data["character"]
        # 한 만화 전체에서만 유지되는 Master Seed를 한 번만 만든다.
        # 이후 1~4컷 Panel에는 동일 seed를 넣어 컷 간 stochastic variation을 줄인다.
        master_seed = random.randint(0, 2**32 - 1)
        requested_style = clean_panel_text(style)

        comic = Comic(
            idea=idea.strip(),
            title=str(data.get("title") or "4컷 만화"),
            style=str(data.get("style") or style or "comic"),
            character=Character(
                name=str(character.get("name") or "Character"),
                appearance=str(character.get("appearance") or ""),
                personality=str(character.get("personality") or ""),
            ),
            master_seed=master_seed,
            style_prompt=requested_style or clean_panel_text(str(data.get("style") or "comic")),
        )
        for i, p in enumerate(data["panels"]):
            comic.panels.append(Panel(
                i + 1,
                str(p.get("scene") or ""),
                str(p.get("image_prompt") or ""),
                str(p.get("dialogue") or ""),
                str(p.get("speaker") or ""),
                seed=master_seed,
            ))

        # Character Prompt / Style Prompt는 이 만화 생성 시 1회만 확정하고
        # 아래 모든 패널에서 같은 문자열을 그대로 재사용한다.
        # 전체 다시 만들기처럼 이전 세션의 캐릭터 프롬프트가 전달되면
        # 동일한 캐릭터 외형을 유지하기 위해 그것을 우선한다.
        if str(character_prompt or "").strip():
            char = clean_panel_text(character_prompt)
        else:
            char = clean_panel_text(comic.character.visual_prompt())
        style_text = clean_panel_text(comic.style_prompt)
        comic.character_prompt = char
        for p in comic.panels:
            p.image_prompt = (
                f"{char}. Scene: {clean_panel_text(p.image_prompt)}. Style: {style_text}. "
                "Preserve and visibly render the background/environment described by this scene. "
                "Do not replace the scene background with a blank or pure-white backdrop unless the scene explicitly calls for white. "
                "Background detail can be simple and secondary to the characters. "
                "Single frame illustration, solo main subject, single camera angle, "
                "no split screen, no grid layout, no multiple panels, consistent character design, clear composition."
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
