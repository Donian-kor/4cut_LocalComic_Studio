from PySide6.QtCore import QThread, Signal


class ComicWorker(QThread):
    """전체 4컷 생성 파이프라인.

    진행 단계는 텍스트 파싱이 아닌 타입 있는 신호로 알린다.
    progress 신호는 UI 표시용 문구 전용이다.
    cancel()은 플래그만 설정한다. ComfyUI interrupt는 worker 스레드 안의
    wait_for_image가 감지해 1회 호출한다(UI 스레드에서 네트워크 호출 금지).
    """

    progress = Signal(str, int, int)        # 표시용 문구
    planned = Signal(object)                # 스토리 계획 확정(세션 저장 시점)
    panel_started = Signal(int)             # N컷 생성 시작
    panel_completed = Signal(int, str, str)  # index, path, dialogue_status
    compose_started = Signal()              # 최종 합성 시작
    finished_comic = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, comic_service, idea, style="", character_prompt=""):
        super().__init__()
        self.service = comic_service
        self.idea = idea
        self.style = style
        self.character_prompt = character_prompt
        self.cancel_requested = False
        self.comic = None

    def cancel(self):
        # UI 스레드에서 네트워크 요청을 하지 않는다. 플래그만 설정한다.
        self.cancel_requested = True

    def run(self):
        try:
            self.progress.emit("아이디어 분석 및 4컷 스토리 생성", 0, 4)
            self.service.begin_run()
            comic = self.service.plan(
                self.idea,
                self.style,
                cancel_check=lambda: self.cancel_requested,
                character_prompt=self.character_prompt or None,
            )
            self.comic = comic
            self.planned.emit(comic)
            if self.cancel_requested:
                self.cancelled.emit(); return

            for i, panel in enumerate(comic.panels):
                if self.cancel_requested:
                    self.cancelled.emit(); return
                self.panel_started.emit(i + 1)
                self.progress.emit(f"{i + 1}컷 이미지 생성 중", i, 4)
                # ComicService가 확정한 Master Seed / Character Prompt / Style Prompt를
                # 모든 패널에 공유한다. style은 패널마다 새로 계산하지 않는다.
                path = self.service.generate_panel(comic, panel, cancel_check=lambda: self.cancel_requested)
                status = str(getattr(panel, "dialogue_status", "") or "")
                self.panel_completed.emit(i + 1, path or panel.image_path, status)
                self.progress.emit(f"{i + 1}컷 생성 완료", i + 1, 4)

            if self.cancel_requested:
                self.cancelled.emit(); return
            self.compose_started.emit()
            self.progress.emit("4컷 합성 중", 4, 4)
            self.service.compose(comic)
            if self.cancel_requested:
                self.cancelled.emit(); return
            self.finished_comic.emit(comic)
        except InterruptedError:
            self.cancelled.emit()
        except Exception as e:
            if self.cancel_requested:
                self.cancelled.emit()
            else:
                self.failed.emit(str(e))
