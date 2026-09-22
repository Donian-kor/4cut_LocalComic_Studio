class GenerationController:
    def __init__(self, widget):
        self.widget = widget
        self.worker = None

    def set_generating(self, generating):
        self.widget.set_generating(generating)

    def set_status(self, message, current, total):
        self.widget.set_status(message, current, total)

    def attach_worker(self, worker):
        self.worker = worker
        worker.progress.connect(self._progress)
        if hasattr(worker, "panel_completed"):
            worker.panel_completed.connect(self._panel_completed)
        worker.finished_comic.connect(self._finished)
        worker.failed.connect(self._failed)
        worker.cancelled.connect(self._cancelled)
        self.widget.set_generating(True)
        self.widget.set_status("아이디어 분석 및 4컷 스토리 생성 중...", 0, 4)

    def cancel(self):
        if self.worker and self.worker.isRunning():
            self.widget.set_generating(False)
            self.worker.cancel()

    def _progress(self, message, current, total):
        self.widget.set_status(message, current, total)

    def _panel_completed(self, index, path):
        if hasattr(self.widget, "set_panel_thumbnail"):
            self.widget.set_panel_thumbnail(index, path)

    def _finished(self, comic):
        self.widget.set_generating(False)
        self.worker = None

    def _failed(self, message):
        self.widget.set_generating(False)
        if hasattr(self.widget, "set_failed"):
            self.widget.set_failed(message)
        else:
            self.widget.set_status(f"오류: {message}", 0, 4)
        self.worker = None

    def _cancelled(self):
        self.widget.set_generating(False)
        if hasattr(self.widget, "set_cancelled"):
            self.widget.set_cancelled()
        else:
            self.widget.set_status("생성이 취소되었습니다.", 0, 4)
        self.worker = None
