from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
from core.workers.comic_worker import ComicWorker
from features.generation.controller import GenerationController
from features.preview.controller import PreviewController
from features.result.controller import ResultController


class MainController(QObject):
    def __init__(self, main_window, service_factory):
        super().__init__()
        self.window = main_window
        self.service_factory = service_factory
        self.service = service_factory()
        self.generation = GenerationController(main_window.generation)
        self.preview = PreviewController(main_window.preview)
        self.result = ResultController(main_window.result)
        self.last_idea = ""
        self.last_style = ""
        self.workers = []  # 실행 중인 ComicWorker 참조 보관 (조기 GC 방지)
        main_window.idea.generateRequested.connect(self.start_generation)
        main_window.generation.cancelRequested.connect(self.cancel_generation)
        main_window.result.regenerateRequested.connect(self.regenerate)
        main_window.settingsApplied.connect(self.settings_changed)

    def settings_changed(self):
        if self.generation.worker and self.generation.worker.isRunning():
            return
        self.service = self.service_factory()

    def start_generation(self, idea, style):
        if self.generation.worker and self.generation.worker.isRunning():
            return
        if not idea.strip():
            QMessageBox.warning(self.window, "아이디어 필요", "4컷 만화 아이디어를 입력해 주세요.")
            return
        self.last_idea, self.last_style = idea.strip(), style.strip()
        self.window.idea.set_enabled(False)
        worker = ComicWorker(self.service, self.last_idea, self.last_style)
        self.generation.attach_worker(worker)
        self.workers.append(worker)
        worker.finished_comic.connect(self.on_finished)
        worker.failed.connect(self.on_failed)
        worker.cancelled.connect(self.on_cancelled)
        worker.finished.connect(self.release_worker)
        worker.start()

    def release_worker(self):
        """스레드가 완전히 끝난 뒤에만 ComicWorker 참조를 놓는다.

        run() 이 반환되기 전에 ComicWorker 참조가 사라지면 QThread 객체가
        파괴되면서 'QThread: Destroyed while thread ... is still running' 과 함께
        프로세스가 즉시 종료된다.
        """
        worker = self.sender()
        if worker is None:
            return
        worker.wait()
        if worker in self.workers:
            self.workers.remove(worker)

    def cancel_generation(self):
        self.generation.cancel()

    def on_finished(self, comic):
        self.window.idea.set_enabled(True)
        self.preview.show_comic(comic)
        self.result.show_result(comic)

    def on_failed(self, message):
        self.window.idea.set_enabled(True)
        QMessageBox.critical(self.window, "생성 실패", message)

    def on_cancelled(self):
        self.window.idea.set_enabled(True)

    def regenerate(self):
        if self.last_idea:
            self.start_generation(self.last_idea, self.last_style)
