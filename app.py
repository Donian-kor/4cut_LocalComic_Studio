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


def build_service(settings):
    lm_settings = dict(settings.section("lmstudio"))
    comfy_settings = dict(settings.section("comfyui"))
    lm = LMStudioClient(lm_settings)
    comfy = ComfyUIClient(comfy_settings)
    workflow = WorkflowAdapter(comfy_settings.get("workflow", "workflows/4cut_default.json"), settings.base_dir)
    return ComicService(lm, comfy, workflow, settings.data, settings.base_dir)


def main():
    app = QApplication(sys.argv)
    settings = SettingsManager()
    window = MainWindow(settings, LMStudioClient, ComfyUIClient)
    controller = MainController(window, lambda: build_service(settings))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
