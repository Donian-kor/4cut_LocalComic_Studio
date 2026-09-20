from pathlib import Path
from PySide6.QtCore import QObject
from core.workers.comic_worker import ComicWorker
from features.generation.controller import GenerationController
from features.preview.controller import PreviewController
from features.result.controller import ResultController

class MainController(QObject):
    def __init__(self, main_window, comic_service):
        super().__init__()
        self.window = main_window
        self.service = comic_service
        self.generation = GenerationController(main_window.generation)
        self.preview = PreviewController(main_window.preview)
        self.result = ResultController(main_window.result)
        self.last_idea = ""
        self.last_style = ""
        main_window.idea.generateRequested.connect(self.start_generation)
        main_window.generation.cancelRequested.connect(self.cancel_generation)
        main_window.result.regenerateRequested.connect(self.regenerate)

    def start_generation(self, idea, style):
        self.last_idea, self.last_style = idea, style
        self.window.idea.set_enabled(False)
        worker = ComicWorker(self.service, idea, style)
        self.generation.attach_worker(worker)
        worker.finished_comic.connect(self.on_finished)
        worker.failed.connect(lambda _: self.window.idea.set_enabled(True))
        worker.cancelled.connect(lambda: self.window.idea.set_enabled(True))
        self.generation.worker = worker
        worker.start()

    def cancel_generation(self):
        self.generation.cancel()

    def on_finished(self, comic):
        self.window.idea.set_enabled(True)
        self.preview.show_comic(comic)
        self.result.show_result(comic)

    def regenerate(self):
        if self.last_idea:
            self.start_generation(self.last_idea, self.last_style)
