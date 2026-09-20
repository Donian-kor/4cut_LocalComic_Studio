from pathlib import Path
from datetime import datetime
from core.services.story_service import StoryService
from core.services.image_service import ImageService
from core.services.compose_service import ComposeService

class ComicService:
    def __init__(self, llm_client, comfy_client, workflow_adapter, settings):
        self.llm_client = llm_client
        self.comfy_client = comfy_client
        self.story = StoryService(llm_client)
        general = settings.get("general", {})
        width = int(general.get("width", 768))
        height = int(general.get("height", 768))
        self.image = ImageService(comfy_client, workflow_adapter, width, height)
        self.compose_service = ComposeService()
        self.project_path = Path(general.get("project_path", "projects"))

    def plan(self, idea, style=""):
        return self.story.create_comic(idea, style)

    def generate_panel(self, comic, panel):
        folder = self.project_path / "current"
        return self.image.generate_panel(panel, folder)

    def compose(self, comic):
        folder = self.project_path / "current"
        folder.mkdir(parents=True, exist_ok=True)
        return self.compose_service.compose(comic, folder / "final_4cut.png")

    def cancel_image_generation(self):
        self.comfy_client.interrupt()
