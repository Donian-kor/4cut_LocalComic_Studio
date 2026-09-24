# -*- coding: utf-8 -*-
"""ComicWorker/PanelRegenerationWorker의 신호 계약(타입 있는 단계 신호)을 검증한다.

worker.cancel()은 UI 스레드에서 네트워크를 호출하지 않고 플래그만 설정해야 한다.
"""
from studio.workers.comic_worker import ComicWorker
from studio.workers.panel_regeneration_worker import PanelRegenerationWorker


class _RecordingService:
    def __init__(self):
        self.interrupted = 0

    def cancel_image_generation(self):
        self.interrupted += 1


def test_comic_worker_cancel_only_sets_flag():
    service = _RecordingService()
    worker = ComicWorker(service, "아이디어", "style")

    worker.cancel()

    assert worker.cancel_requested is True
    assert service.interrupted == 0, "UI 스레드 cancel()은 네트워크 interrupt를 호출하면 안 된다"


def test_panel_regen_worker_cancel_only_sets_flag():
    service = _RecordingService()
    worker = PanelRegenerationWorker(service, comic=None, panel_index=1, revision="")

    worker.cancel()

    assert worker.cancel_requested is True
    assert service.interrupted == 0


def test_worker_declares_typed_step_signals():
    # 텍스트 파싱 대신 사용하는 타입 있는 단계 신호들이 선언되어 있어야 한다
    for signal_name in ("progress", "planned", "panel_started", "panel_completed",
                        "compose_started", "finished_comic", "failed", "cancelled"):
        assert hasattr(ComicWorker, signal_name)
    for signal_name in ("panel_started", "panel_generated", "compose_started",
                        "finished_comic", "failed", "cancelled"):
        assert hasattr(PanelRegenerationWorker, signal_name)
    # 구버전 panel_completed 신호는 제거되었다
    assert not hasattr(PanelRegenerationWorker, "panel_completed")
