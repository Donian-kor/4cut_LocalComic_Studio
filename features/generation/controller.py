class GenerationController:
    def __init__(self, widget):
        self.widget = widget
        self.worker = None

    def attach_worker(self, worker):
        self.worker = worker
        worker.progress.connect(self._progress)
        worker.finished_comic.connect(self._finished)
        worker.failed.connect(self._failed)
        worker.cancelled.connect(self._cancelled)
        self.widget.set_generating(True)

    def cancel(self):
        if self.worker and self.worker.isRunning():
            self.widget.set_cancel_enabled(False)
            self.worker.cancel()

    def _progress(self, message, current, total):
        self.widget.set_status(message, current, total)

    def _finished(self, comic):
        self.widget.set_generating(False)
        self.worker = None

    def _failed(self, message):
        self.widget.set_generating(False)
        self.widget.set_status(f"오류: {message}", 0, 4)
        self.worker = None

    def _cancelled(self):
        self.widget.set_generating(False)
        self.widget.set_status("생성이 취소되었습니다.", 0, 4)
        self.worker = None
