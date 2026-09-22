from pathlib import Path
from datetime import datetime
from core.services.story_service import StoryService
from core.services.image_service import ImageService
from core.services.compose_service import ComposeService


class ComicService:
    def __init__(self, llm_client, comfy_client, workflow_adapter, settings, base_dir=None, image_model=None):
        self.llm_client = llm_client
        self.comfy_client = comfy_client
        self.workflow = workflow_adapter
        self.image_model = image_model
        self.story = StoryService(llm_client)
        general = settings.get("general", {})
        self.width = int(getattr(image_model, "width", general.get("width", 768)))
        self.height = int(getattr(image_model, "height", general.get("height", 768)))
        self.image = ImageService(comfy_client, workflow_adapter, self.width, self.height)
        self.compose_service = ComposeService()
        self.font_name = self._resolve_font_name(workflow_adapter)
        self.project_path = Path(general.get("project_path", "projects"))
        if not self.project_path.is_absolute() and base_dir:
            self.project_path = Path(base_dir) / self.project_path
        self.auto_save = bool(general.get("auto_save", True))
        # 분위기(장르) + 그림체(아트 스타일) 프롬프트를 결합한다.
        # 그림체가 시각적 렌더링에 더 직접적이므로 앞쪽에 배치한다.
        mood_prompt = str(general.get("style_prompt", "") or "")
        art_style_prompt = str(general.get("art_style_prompt", "") or "")
        parts = [p for p in (art_style_prompt, mood_prompt) if p]
        self.style_prompt = ", ".join(parts)
        self._run_folder = None

    @staticmethod
    def _resolve_font_name(workflow_adapter):
        """폰트 절대 경로를 DrawText+ 폰트 폴더 기준 파일명으로 변환한다."""
        font_path = getattr(workflow_adapter, "font_path", "") or ""
        return Path(font_path).name if font_path else "malgun.ttf"

    def plan(self, idea, style="", cancel_check=None):
        return self.story.create_comic(idea, style, cancel_check=cancel_check)

    def begin_run(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")[:-3]
        if self.auto_save:
            folder = self.project_path / timestamp
        else:
            folder = self.project_path / ".cache" / timestamp
        folder.mkdir(parents=True, exist_ok=True)
        self._run_folder = folder
        return folder

    def generate_panel(self, comic, panel, cancel_check=None, style_prompt=None):
        folder = self._run_folder or self.begin_run()
        # 외부에서 전달된 style(우선순위 높음)이 있으면 그것을, 없으면 설정 기반 self.style_prompt를 사용한다.
        path = self.image.generate_panel(
            panel, folder,
            cancel_check=cancel_check,
            style_prompt=style_prompt or self.style_prompt,
        )
        # 2단계: 말풍선 감지 기반 대사 합성. 2단계 workflow가 없으면 생략한다.
        if getattr(self.workflow, "stage2_path", None):
            try:
                self.image.apply_dialogue(
                    panel,
                    font_name=self.font_name,
                    cancel_check=cancel_check,
                )
            except InterruptedError:
                raise
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"[ComicService] 패널 {panel.index} 2단계 대사 합성 중 예외 발생: {e}")
        return panel.image_path or path

    def compose(self, comic):
        folder = self._run_folder or self.begin_run()
        return self.compose_service.compose(comic, folder / "final_4cut.png")

    def cancel_image_generation(self):
        self.comfy_client.interrupt()
