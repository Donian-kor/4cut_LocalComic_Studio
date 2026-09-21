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
        self.project_path = Path(general.get("project_path", "projects"))
        if not self.project_path.is_absolute() and base_dir:
            self.project_path = Path(base_dir) / self.project_path
        self.auto_save = bool(general.get("auto_save", True))
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
        return self.image.generate_panel(panel, folder, cancel_check=cancel_check)

    def compose(self, comic):
        folder = self._run_folder or self.begin_run()
        return self.compose_service.compose(comic, folder / "final_4cut.png")

    def cancel_image_generation(self):
        self.comfy_client.interrupt()
