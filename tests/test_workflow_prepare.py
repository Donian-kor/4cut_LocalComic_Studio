# -*- coding: utf-8 -*-
"""stage2 정규화와 negative 프롬프트 병합/조건부 적용을 검증한다."""
import json
from types import SimpleNamespace

import pytest

from integrations.comfyui.workflow import WorkflowAdapter

PROFILE = SimpleNamespace(
    width=512,
    height=512,
    steps=28,
    cfg=4.0,
    sampler="euler",
    scheduler="normal",
    model_file="m.safetensors",
    negative_prompt="profile negative",
)


def _make_workflow(tmp_path, negative_text=""):
    data = {
        "1": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": negative_text}},
        "3": {"class_type": "KSampler", "inputs": {
            "seed": 1, "steps": 1, "cfg": 1,
            "sampler_name": "euler", "scheduler": "normal",
        }},
    }
    path = tmp_path / "wf.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_missing_stage2_file_normalized_to_none(tmp_path):
    adapter = WorkflowAdapter(
        _make_workflow(tmp_path),
        base_dir=tmp_path,
        profile=PROFILE,
        stage2_path="missing_stage2.json",
    )
    # 조립 시점에 파일 존재를 검증해 None으로 정규화한다
    assert adapter.stage2_path is None
    with pytest.raises(FileNotFoundError):
        adapter.prepare_stage2("img.png", "대사")


def test_existing_stage2_keeps_path(tmp_path):
    stage2 = tmp_path / "wf_stage2.json"
    stage2.write_text("{}", encoding="utf-8")
    adapter = WorkflowAdapter(
        _make_workflow(tmp_path), base_dir=tmp_path, profile=PROFILE, stage2_path="wf_stage2.json"
    )
    assert adapter.stage2_path == stage2


def test_negative_merges_workflow_text_and_profile(tmp_path):
    adapter = WorkflowAdapter(
        _make_workflow(tmp_path, negative_text="workflow custom neg"), profile=PROFILE
    )
    wf = adapter.prepare("a character in a forest", seed=7)
    neg = wf["2"]["inputs"]["text"]
    # 워크플로우 기존 negative를 덮어쓰지 않고 병합한다
    assert "workflow custom neg" in neg
    assert "profile negative" in neg
    # 텍스트 금지 정책은 유지한다
    assert "text" in neg
    # 흰 배경 미요청 → 배경 관련 negative 포함
    assert "blank background" in neg


def test_background_negative_skipped_when_white_requested(tmp_path):
    adapter = WorkflowAdapter(
        _make_workflow(tmp_path, negative_text="workflow custom neg"), profile=PROFILE
    )
    wf = adapter.prepare("sticker character on white background", seed=7)
    neg = wf["2"]["inputs"]["text"]
    # 사용자가 명시적으로 흰 배경을 요청하면 배경 negative와 충돌하지 않도록 생략
    assert "workflow custom neg" in neg
    assert "blank background" not in neg
    assert "pure white background" not in neg
    assert "isolated on white" not in neg
    # 텍스트 금지와 말풍선 유도는 유지된다
    assert "text" in neg
    assert "speech bubble" in wf["1"]["inputs"]["text"].lower()