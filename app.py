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
from ui import theme
from app.main_controller import MainController
from app.version import APP_NAME, APP_VERSION


def build_service(settings, model_id=None):
    lm_settings = dict(settings.section("lmstudio"))
    comfy_settings = dict(settings.section("comfyui"))
    lm = LMStudioClient(lm_settings)
    comfy = ComfyUIClient(comfy_settings)
    model_manager = ImageModelManager(settings)
    profile = model_manager.get(model_id or None)
    if profile is None:
        raise RuntimeError("사용할 이미지 모델 프로필이 없습니다.")
    workflow = WorkflowAdapter(
        profile.workflow, settings.base_dir, profile,
        font_path=comfy_settings.get("font_path", ""),
        stage2_path=(getattr(profile, "stage2_workflow", "") or profile.workflow.replace(".json", "_stage2.json")),
    )
    return ComicService(lm, comfy, workflow, settings.data, settings.base_dir, image_model=profile)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    settings = SettingsManager()
    theme.apply_font(settings.data.get("general", {}).get("ui_font_family"))
    window = MainWindow(settings, LMStudioClient, ComfyUIClient)
    controller = MainController(window, lambda model_id=None: build_service(settings, model_id))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
