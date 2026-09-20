import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from settings.settings_manager import SettingsManager
from integrations.lmstudio.client import LMStudioClient
from integrations.comfyui.client import ComfyUIClient
from integrations.comfyui.workflow import WorkflowAdapter
from core.services.comic_service import ComicService
from ui.main.main_window import MainWindow
from app.main_controller import MainController

def main():
    app = QApplication(sys.argv)
    settings = SettingsManager()
    lm = LMStudioClient(settings.section("lmstudio"))
    comfy = ComfyUIClient(settings.section("comfyui"))
    workflow = WorkflowAdapter(settings.section("comfyui").get("workflow", "workflows/4cut_default.json"))
    service = ComicService(lm, comfy, workflow, settings.data)

    window = MainWindow(
        settings,
        lambda s: LMStudioClient(s),
        lambda s: ComfyUIClient(s)
    )
    controller = MainController(window, service)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
