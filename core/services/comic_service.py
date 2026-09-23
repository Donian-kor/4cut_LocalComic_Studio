from pathlib import Path
from datetime import datetime
import random
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
        comic = self.story.create_comic(idea, style, cancel_check=cancel_check)
        # 실제 생성에 사용하는 모델/샘플러 설정을 이번 만화의 생성 컨텍스트에
        # 스냅샷으로 남긴다. service는 Worker 한 번의 실행 동안 동일 profile을 사용한다.
        profile = self.image_model
        if profile is not None:
            comic.generation_config = {
                "id": str(getattr(profile, "id", "")),
                "name": str(getattr(profile, "name", "")),
                "model_file": str(getattr(profile, "model_file", "")),
                "width": int(getattr(profile, "width", self.width)),
                "height": int(getattr(profile, "height", self.height)),
                "steps": int(getattr(profile, "steps", 28)),
                "cfg": float(getattr(profile, "cfg", 4.0)),
                "sampler": str(getattr(profile, "sampler", "euler_ancestral")),
                "scheduler": str(getattr(profile, "scheduler", "beta")),
            }
        return comic

    def set_run_folder(self, folder):
        self._run_folder = Path(folder)
        self._run_folder.mkdir(parents=True, exist_ok=True)
        return self._run_folder

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
        # 이번 Comic에서 1회 확정한 style_prompt를 모든 패널에 동일하게 사용한다.
        fixed_style_prompt = getattr(comic, "style_prompt", "") or self.style_prompt
        path = self.image.generate_panel(
            panel, folder,
            cancel_check=cancel_check,
            style_prompt=fixed_style_prompt,
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

    def regenerate_panel(self, comic, panel_index, revision="", cancel_check=None):
        """기존 Comic 계획을 재사용해 지정한 패널만 다시 생성한다.

        최종 4컷 합성은 Worker가 패널 결과를 UI에 반영한 뒤 별도 단계로 호출한다.
        """
        try:
            index = int(panel_index)
        except (TypeError, ValueError) as exc:
            raise ValueError("유효하지 않은 패널 번호입니다.") from exc
        if not comic or not (1 <= index <= len(comic.panels)):
            raise ValueError("재생성할 패널을 찾을 수 없습니다.")

        panel = comic.panels[index - 1]
        revision = str(revision or "").strip()
        panel.revision_prompt = revision
        panel.revision_count = int(getattr(panel, "revision_count", 0) or 0) + 1
        # 전체 만화의 Master Seed는 기준값으로 유지하고, 선택 컷만 새 revision seed를 사용한다.
        panel.seed = random.randint(0, 2**32 - 1)

        base_folder = self._run_folder
        if base_folder is None:
            if comic.output_path:
                base_folder = Path(comic.output_path).parent
            else:
                base_folder = self.begin_run()
        base_folder = Path(base_folder)
        revision_dir = base_folder / "revisions" / f"panel_{index}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
        revision_dir.mkdir(parents=True, exist_ok=True)
        fixed_style_prompt = getattr(comic, "style_prompt", "") or self.style_prompt
        path = self.image.generate_panel(
            panel, revision_dir, cancel_check=cancel_check, style_prompt=fixed_style_prompt
        )
        if getattr(self.workflow, "stage2_path", None):
            try:
                self.image.apply_dialogue(
                    panel, font_name=self.font_name, cancel_check=cancel_check
                )
            except InterruptedError:
                raise
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"[ComicService] 패널 {panel.index} 재생성 대사 합성 중 예외 발생: {e}")
        return panel.image_path or path

    def cancel_image_generation(self):
        self.comfy_client.interrupt()
