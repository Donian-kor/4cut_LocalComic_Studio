import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from settings.settings_manager import SettingsManager
from integrations.lmstudio.client import LMStudioClient
from integrations.comfyui.client import ComfyUIClient
from integrations.comfyui.workflow import WorkflowAdapter
from settings.model_manager import ImageModelManager
from core.services.comic_service import ComicService
from ui.main.main_window import MainWindow
from app.main_controller import MainController


def build_service(settings):
    lm_settings = dict(settings.section("lmstudio"))
    comfy_settings = dict(settings.section("comfyui"))
    lm = LMStudioClient(lm_settings)
    comfy = ComfyUIClient(comfy_settings)
    model_manager = ImageModelManager(settings)
    profile = model_manager.get()
    if profile is None:
        raise RuntimeError("사용할 이미지 모델 프로필이 없습니다.")
    workflow = WorkflowAdapter(
        profile.workflow, settings.base_dir, profile,
        font_path=comfy_settings.get("font_path", ""),
        font_size=comfy_settings.get("font_size", 32),
        stage2_path=profile.workflow.replace(".json", "_stage2.json"),
    )
    return ComicService(lm, comfy, workflow, settings.data, settings.base_dir, image_model=profile)


def main():
    app = QApplication(sys.argv)
    settings = SettingsManager()
    window = MainWindow(settings, LMStudioClient, ComfyUIClient)
    controller = MainController(window, lambda: build_service(settings))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
