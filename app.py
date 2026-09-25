import sys
from PySide6.QtWidgets import QApplication
from studio.settings.settings_manager import SettingsManager
from studio.services.session_manager import SessionManager
from studio.integrations.lmstudio import LMStudioClient
from studio.integrations.comfyui import ComfyUIClient
from studio.integrations.workflow import WorkflowAdapter
from studio.settings.model_manager import ImageModelManager
from studio.services.comic_service import ComicService
from studio.ui.main_window import MainWindow
from studio.ui import theme
from studio.main_controller import MainController
from studio.version import APP_NAME, APP_VERSION


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
    app.setApplicationVersion(APP_VERSION)
    settings = SettingsManager()
    theme.apply_font(settings.data.get("general", {}).get("ui_font_family"))
    session_manager = SessionManager(settings)
    window = MainWindow(settings, LMStudioClient, ComfyUIClient, session_manager=session_manager)
    controller = MainController(window, lambda model_id=None: build_service(settings, model_id), session_manager=session_manager)
    controller.initialize()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
