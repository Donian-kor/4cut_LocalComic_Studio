from PySide6.QtCore import QThread, Signal


class PanelRegenerationWorker(QThread):
    """단일 컷 재생성 + 자동 최종 합성.

    panel_generated는 UI 진행 표시 전용이다. 패널/결과/카드의 세션 반영은
    최종 합성까지 성공한 finished_comic 시점에 한 번만 커밋된다.
    cancel()은 플래그만 설정한다(네트워크 interrupt는 worker 스레드에서 발생).
    """

    panel_started = Signal(int)
    panel_generated = Signal(int, str)  # 중간 진행 표시 전용 — 세션 커밋 아님
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
        # UI 스레드에서 네트워크 요청을 하지 않는다. 플래그만 설정한다.
        # 실제 ComfyUI interrupt는 wait_for_image의 취소 감지 지점(worker 스레드)에서
        # 1회 호출된다.
        self.cancel_requested = True

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
            self.panel_generated.emit(self.panel_index, path or "")
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
