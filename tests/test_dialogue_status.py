# -*- coding: utf-8 -*-
"""2단계 대사 합성 상태가 Panel.dialogue_status에 정확히 기록되는지 검증한다."""
import pytest

from core.models.comic import Panel
from core.services.comic_service import ComicService


class _Workflow:
    def __init__(self, stage2=None):
        self.stage2_path = stage2


class _ImageOK:
    def apply_dialogue(self, panel, **kwargs):
        panel.dialogue_composited = True
        return panel.image_path


class _ImageBoom:
    def apply_dialogue(self, panel, **kwargs):
        raise RuntimeError("stage2 실패")


class _ImageInterrupt:
    def apply_dialogue(self, panel, **kwargs):
        raise InterruptedError("취소")


def _service(image, stage2=None):
    service = ComicService.__new__(ComicService)
    service.image = image
    service.workflow = _Workflow(stage2)
    service.font_name = "malgun.ttf"
    return service


def _panel(dialogue="대사"):
    return Panel(1, scene="", image_prompt="p", dialogue=dialogue, seed=1,
                 image_path="panel_1.png")


def test_stage2_success_marks_composited():
    panel = _panel()
    _service(_ImageOK(), stage2="wf_stage2.json")._apply_stage2(panel)
    assert panel.dialogue_status == "composited"


def test_stage2_failure_marks_failed():
    panel = _panel()
    _service(_ImageBoom(), stage2="wf_stage2.json")._apply_stage2(panel)
    assert panel.dialogue_status == "failed"


def test_missing_stage2_marks_skipped():
    panel = _panel()
    _service(_ImageOK(), stage2=None)._apply_stage2(panel)
    assert panel.dialogue_status == "skipped"


def test_empty_dialogue_marks_none_without_calling_stage2():
    panel = _panel(dialogue="")
    _service(_ImageBoom(), stage2="wf.json")._apply_stage2(panel)
    assert panel.dialogue_status == "none"


def test_cancel_propagates_interrupted_without_status_change():
    panel = _panel()
    with pytest.raises(InterruptedError):
        _service(_ImageInterrupt(), stage2="wf.json")._apply_stage2(panel)