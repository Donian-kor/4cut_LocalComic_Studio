from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
from core.workers.comic_worker import ComicWorker
from features.generation.controller import GenerationController
from features.preview.controller import PreviewController
from features.result.controller import ResultController


class MainController(QObject):
    def __init__(self, main_window, service_factory):
        super().__init__(main_window)
        self.window = main_window
        self.service_factory = service_factory
        self.service = None
        self.generation = GenerationController(main_window.generation)
        self.preview = PreviewController(main_window.preview)
        self.result = ResultController(main_window.result)
        self.last_idea = ""
        self.last_style = ""
        self.last_revision = ""
        self.workers = []
        self._is_revising = False

        main_window.idea.generateRequested.connect(self.start_generation)
        main_window.generation.cancelRequested.connect(self.cancel_generation)
        main_window.result.regenerateRequested.connect(self.regenerate)
        main_window.result.revisionRequested.connect(self.revise)
        main_window.settingsApplied.connect(self.settings_changed)
        self.generation.worker = None

    def settings_changed(self):
        if self.generation.worker and self.generation.worker.isRunning():
            return
        try:
            self.service = self.service_factory()
        except Exception as e:
            self.service = None
            QMessageBox.warning(self.window, "설정 확인 필요", f"AI 생성 설정을 준비하지 못했습니다.\n\n{e}")

    def start_generation(self, idea, style):
        if self.generation.worker and self.generation.worker.isRunning():
            return
        if not idea.strip():
            QMessageBox.warning(self.window, "아이디어 필요", "4컷 만화 아이디어를 입력해 주세요.")
            return
        lm_ok, comfy_ok = getattr(self.window, "_server_state", (False, False))
        if not (lm_ok and comfy_ok):
            self._is_revising = False
            self.window.result.set_revision_enabled(True)
            QMessageBox.warning(
                self.window,
                "AI 서버 연결 필요",
                "LM Studio와 ComfyUI가 모두 연결되어야 4컷 만화를 만들 수 있습니다.\n\n설정에서 서버를 실행하고 연결 테스트를 확인해 주세요.",
            )
            self.window.refresh_server_status()
            return

        try:
            self.service = self.service_factory()
        except Exception as e:
            self._is_revising = False
            self.window.result.set_revision_enabled(True)
            QMessageBox.critical(self.window, "생성 설정 오류", f"현재 AI 생성 설정을 사용할 수 없습니다.\n\n{e}")
            return

        self.last_idea = idea.strip()
        self.last_style = style.strip()
        self.window.idea.set_enabled(False)
        if not self._is_revising:
            self.window.result.set_revision_enabled(True)
        self.window.show_generation_page()
        self.generation.set_generating(True)
        self.generation.set_status("생성을 준비하는 중...", 0, 4)

        worker = ComicWorker(self.service, self.last_idea, self.last_style)
        self.generation.attach_worker(worker)
        self.workers.append(worker)
        worker.progress.connect(self.generation.set_status)
        worker.finished_comic.connect(self.on_finished)
        worker.failed.connect(self.on_failed)
        worker.cancelled.connect(self.on_cancelled)
        worker.finished.connect(self.release_worker)
        worker.start()

    def release_worker(self):
        worker = self.sender()
        if worker is None:
            return
        worker.wait()
        if worker in self.workers:
            self.workers.remove(worker)

    def cancel_generation(self):
        self.generation.cancel()

    def on_finished(self, comic):
        self._is_revising = False
        self.window.idea.set_enabled(True)
        self.generation.set_generating(False)
        self.window.result.set_revision_enabled(True)
        self.preview.show_comic(comic)
        self.result.show_result(comic)
        self.window.show_result_page()

    def on_failed(self, message):
        was_revising = self._is_revising
        self._is_revising = False
        self.window.idea.set_enabled(True)
        self.generation.set_generating(False)
        self.window.result.set_revision_enabled(True)
        if was_revising and getattr(self.window.result, "comic", None):
            self.window.show_result_page()
        else:
            self.window.show_idea_page()
        QMessageBox.critical(self.window, "생성 실패", message)

    def on_cancelled(self):
        was_revising = self._is_revising
        self._is_revising = False
        self.window.idea.set_enabled(True)
        self.generation.set_generating(False)
        self.window.result.set_revision_enabled(True)
        if was_revising and getattr(self.window.result, "comic", None):
            self.window.show_result_page()
        else:
            self.window.show_idea_page()

    def regenerate(self):
        if self.last_idea:
            self.start_generation(self.last_idea, self.last_style)

    def revise(self, revision):
        revision = revision.strip()
        if not revision or not self.last_idea:
            return
        # 현재 엔진은 부분 컷 재생성 API가 없으므로, 사용자의 자연어 수정 요청을
        # 원래 아이디어에 컨텍스트로 붙여 동일한 4컷 생성 파이프라인을 안전하게 재실행한다.
        base_idea = self.last_idea
        revised_idea = f"{base_idea}\n사용자 수정 요청: {revision}"
        self.last_revision = revision
        self._is_revising = True
        self.window.result.set_revision_enabled(False)
        self.start_generation(revised_idea, self.last_style)
        self.last_idea = base_idea
