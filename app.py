import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from studio.settings.settings_manager import SettingsManager
from studio.services.session_manager import SessionManager
from studio.integrations.lmstudio import LMStudioClient
from studio.integrations.comfyui import ComfyUIClient
from studio.integrations.workflow import WorkflowAdapter
from studio.settings.model_manager import ImageModelManager
from studio.services import workflow_factory
from studio.services.comic_service import ComicService
from studio.ui.main_window import MainWindow
from studio.ui import theme
from studio.main_controller import MainController
from studio.version import APP_NAME, APP_VERSION

logger = logging.getLogger(__name__)


def build_service(settings, model_id=None):
    lm_settings = dict(settings.section("lmstudio"))
    comfy_settings = dict(settings.section("comfyui"))
    lm = LMStudioClient(lm_settings)
    comfy = ComfyUIClient(comfy_settings)
    model_manager = ImageModelManager(settings)
    profile = model_manager.get(model_id or None)
    if profile is None:
        raise RuntimeError("사용할 이미지 모델 프로필이 없습니다.")
    workflow_path = profile.workflow
    resolved = settings.resolve_path(workflow_path) if workflow_path else None
    if resolved is None or not resolved.exists():
        # 워크플로우를 몰라도 실행되도록 기본 템플릿으로 자동 생성한다.
        # 실패하더라도 예외를 올리지 않고 Adapter 쪽에서 명확한 오류를 내게 둔다.
        try:
            created = workflow_factory.build_from_template(
                profile.model_file, profile.id, Path(settings.path).parent
            )
            workflow_path = workflow_factory.to_config_path(created, settings.base_dir)
            logger.info("워크플로우 자동 생성: %s", workflow_path)
        except Exception:
            logger.exception("워크플로우 자동 생성 실패: %s", profile.model_file)
    stage2_value = str(getattr(profile, "stage2_workflow", "") or "").strip()
    if not stage2_value:
        resources_dir = Path(settings.path).parent
        stage2_path = workflow_factory.resolve_stage2(
            workflow_path, resources_dir, base_dir=settings.base_dir
        )
        if stage2_path is not None:
            stage2_value = workflow_factory.to_config_path(stage2_path, settings.base_dir)
    workflow = WorkflowAdapter(
        workflow_path or profile.workflow, settings.base_dir, profile,
        font_path=comfy_settings.get("font_path", ""),
        stage2_path=stage2_value or None,
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
