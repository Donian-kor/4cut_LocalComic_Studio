from PySide6.QtCore import QThread, Signal


class ComicWorker(QThread):
    progress = Signal(str, int, int)
    finished_comic = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, comic_service, idea, style=""):
        super().__init__()
        self.service = comic_service
        self.idea = idea
        self.style = style
        self.cancel_requested = False

    def cancel(self):
        self.cancel_requested = True
        try:
            self.service.cancel_image_generation()
        except Exception:
            pass

    def run(self):
        try:
            self.progress.emit("아이디어 분석 및 4컷 스토리 생성", 0, 4)
            self.service.begin_run()
            comic = self.service.plan(self.idea, self.style)
            if self.cancel_requested:
                self.cancelled.emit(); return

            for i, panel in enumerate(comic.panels):
                if self.cancel_requested:
                    self.cancelled.emit(); return
                self.progress.emit(f"{i + 1}컷 이미지 생성 중", i, 4)
                self.service.generate_panel(comic, panel, cancel_check=lambda: self.cancel_requested)
                self.progress.emit(f"{i + 1}컷 이미지 완료", i + 1, 4)

            if self.cancel_requested:
                self.cancelled.emit(); return
            self.progress.emit("4컷 합성 중", 4, 4)
            self.service.compose(comic)
            self.finished_comic.emit(comic)
        except InterruptedError:
            self.cancelled.emit()
        except Exception as e:
            if self.cancel_requested:
                self.cancelled.emit()
            else:
                self.failed.emit(str(e))
