from PySide6.QtCore import QThread, Signal


class PanelRegenerationWorker(QThread):
    panel_started = Signal(int)
    panel_completed = Signal(int, str)
    compose_started = Signal()
    finished_comic = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, comic_service, comic, panel_index, revision=""):
        super().__init__()
        self.service = comic_service
        self.comic = comic
        self.panel_index = int(panel_index)
        self.revision = revision
        self.cancel_requested = False

    def cancel(self):
        self.cancel_requested = True
        try:
            self.service.cancel_image_generation()
        except Exception:
            pass

    def run(self):
        try:
            self.panel_started.emit(self.panel_index)
            path = self.service.regenerate_panel(
                self.comic,
                self.panel_index,
                revision=self.revision,
                cancel_check=lambda: self.cancel_requested,
            )
            if self.cancel_requested:
                self.cancelled.emit()
                return
            self.panel_completed.emit(self.panel_index, path)
            if self.cancel_requested:
                self.cancelled.emit()
                return
            self.compose_started.emit()
            self.service.compose(self.comic)
            if self.cancel_requested:
                self.cancelled.emit()
                return
            self.finished_comic.emit(self.comic)
        except InterruptedError:
            self.cancelled.emit()
        except Exception as e:
            if self.cancel_requested:
                self.cancelled.emit()
            else:
                self.failed.emit(str(e))
