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
        self.compose_service = ComposeService(
            font_size=int(general.get("bubble_font_size", 28) or 28)
        )
        comfy_section = settings.get("comfyui", {}) if isinstance(settings, dict) else {}
        self.font_name = self._resolve_font_name(workflow_adapter)
        self.font_size = int(comfy_section.get("font_size", 32) or 32)

    @staticmethod
    def _resolve_font_name(workflow_adapter):
        """폰트 절대 경로를 DrawText+ 폰트 폴더 기준 파일명으로 변환한다."""
        from pathlib import Path as _P
        font_path = getattr(workflow_adapter, "font_path", "") or ""
        return _P(font_path).name if font_path else "malgun.ttf"
        self.project_path = Path(general.get("project_path", "projects"))
        if not self.project_path.is_absolute() and base_dir:
            self.project_path = Path(base_dir) / self.project_path
        self.auto_save = bool(general.get("auto_save", True))
        self.style_prompt = str(general.get("style_prompt", "") or "")
        self._run_folder = None

    def plan(self, idea, style=""):
        return self.story.create_comic(idea, style)

    def begin_run(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")[:-3]
        if self.auto_save:
            folder = self.project_path / timestamp
        else:
            folder = self.project_path / ".cache" / timestamp
        folder.mkdir(parents=True, exist_ok=True)
        self._run_folder = folder
        return folder

    def generate_panel(self, comic, panel, cancel_check=None):
        folder = self._run_folder or self.begin_run()
        path = self.image.generate_panel(
            panel, folder,
            cancel_check=cancel_check,
            style_prompt=self.style_prompt,
        )
        # 2단계: 말풍선 감지 기반 대사 합성. 2단계 workflow가 없으면 생략한다.
        if getattr(self.workflow, "stage2_path", None):
            try:
                self.image.apply_dialogue(
                    panel,
                    font_name=self.font_name,
                    font_size=self.font_size,
                    cancel_check=cancel_check,
                )
            except InterruptedError:
                raise
            except FileNotFoundError:
                pass
            except Exception:
                # 말풍선이 감지되지 않은 컷 등은 대사 없이 원본 이미지를 유지한다.
                pass
        return path

    def compose(self, comic):
        folder = self._run_folder or self.begin_run()
        return self.compose_service.compose(comic, folder / "final_4cut.png")

    def cancel_image_generation(self):
        self.comfy_client.interrupt()
