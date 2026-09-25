# -*- coding: utf-8 -*-
"""모델 추가용 워크플로우 자동 생성/검증과 설정창 자동 생성 흐름을 검증한다."""
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from studio.services import workflow_factory as wf  # noqa: E402


def _template(resources_dir, model_file="YOUR_MODEL.safetensors"):
    """기본 템플릿(4cut_default.json)과 같은 골격을 가진 임시 템플릿을 만든다."""
    data = {
        "3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model_file}},
        "4": {"class_type": "KSampler", "inputs": {
            "seed": 1, "steps": 1, "cfg": 1.0, "sampler_name": "euler", "scheduler": "normal",
            "positive": ["6", 0], "negative": ["7", 0],
        }},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["4", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "4cut"}},
    }
    resources = Path(resources_dir)
    resources.mkdir(parents=True, exist_ok=True)
    (resources / wf.TEMPLATE_FILENAME).write_text(json.dumps(data), encoding="utf-8")
    (resources / wf.STAGE2_TEMPLATE_FILENAME).write_text(
        json.dumps({"1": {"class_type": "LoadImage", "inputs": {}}}),
        encoding="utf-8",
    )
    return resources


def test_build_from_template_injects_checkpoint_without_touching_template(tmp_path):
    resources = _template(tmp_path)
    path = wf.build_from_template("my-model.safetensors", "My Model", resources)
    assert path.name == "my_model.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["3"]["inputs"]["ckpt_name"] == "my-model.safetensors"
    original = json.loads((resources / wf.TEMPLATE_FILENAME).read_text(encoding="utf-8"))
    assert original["3"]["inputs"]["ckpt_name"] == "YOUR_MODEL.safetensors"
    assert wf.validate_workflow(path, model_file="my-model.safetensors") == []


def test_resolve_stage2_uses_template_for_matching_workflow(tmp_path):
    resources = _template(tmp_path)
    workflow = resources / "my_model.json"
    workflow.write_text("{}", encoding="utf-8")

    resolved = wf.resolve_stage2(workflow, resources)

    assert resolved == resources / "my_model_stage2.json"
    assert resolved.is_file()
    assert json.loads(resolved.read_text(encoding="utf-8"))["1"]["class_type"] == "LoadImage"


def test_build_from_template_needs_template_and_checkpoint_node(tmp_path):
    with pytest.raises(FileNotFoundError):
        wf.build_from_template("m.safetensors", "m", tmp_path)
    resources = Path(tmp_path)
    (resources / wf.TEMPLATE_FILENAME).write_text(
        json.dumps({"9": {"class_type": "SaveImage", "inputs": {}}}), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        wf.build_from_template("m.safetensors", "m", resources)


def test_validate_workflow_reports_missing_nodes_and_placeholder(tmp_path):
    path = tmp_path / "wf.json"
    path.write_text(
        json.dumps({"3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "YOUR_MODEL.safetensors"}}}),
        encoding="utf-8",
    )
    errors = wf.validate_workflow(path)
    assert any("필수 노드" in e for e in errors)
    assert any("체크포인트" in e for e in errors)


def test_validate_workflow_reports_checkpoint_mismatch_and_bad_input(tmp_path):
    resources = _template(tmp_path)
    path = wf.build_from_template("other.safetensors", "other", resources)
    assert any("다릅니다" in e for e in wf.validate_workflow(path, model_file="mine.safetensors"))
    assert wf.validate_workflow(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert wf.validate_workflow(bad)


def test_validate_runnable_accepts_template_copy(tmp_path):
    from studio.models.image_model import ImageModelProfile
    resources = _template(tmp_path)
    path = wf.build_from_template("m.safetensors", "m", resources)
    profile = ImageModelProfile(id="m", name="m", model_file="m.safetensors", workflow=str(path), negative_prompt="")
    assert wf.validate_runnable(path, profile) == []


def test_check_model_file_states():
    class Client:
        def __init__(self, names):
            self.names = names

        def list_checkpoints(self, timeout=5):
            return self.names

    class Broken:
        def list_checkpoints(self, timeout=5):
            raise RuntimeError("연결 실패")

    assert wf.check_model_file(Client(["sub/m.safetensors"]), "m.safetensors")[0] == "ok"
    assert wf.check_model_file(Client(["other.safetensors"]), "m.safetensors")[0] == "missing"
    assert wf.check_model_file(Client([]), "m.safetensors")[0] == "unknown"
    assert wf.check_model_file(Broken(), "m.safetensors")[0] == "unknown"
    assert wf.check_model_file(Client(["m.safetensors"]), "")[0] == "unknown"


class _StubLLM:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.prompts = []

    def chat_json(self, system, user, **kwargs):
        self.prompts.append(user)
        return self.payloads.pop(0)


def test_generate_with_llm_retries_with_feedback_and_saves(tmp_path):
    resources = _template(tmp_path)
    good = json.loads((resources / wf.TEMPLATE_FILENAME).read_text(encoding="utf-8"))
    # 실제 AI 출력처럼 선택한 모델 파일명을 체크포인트에 넣는다.
    good["3"]["inputs"]["ckpt_name"] = "my-model.safetensors"
    llm = _StubLLM([{"1": {"class_type": "SaveImage", "inputs": {}}}, good])
    path = wf.generate_with_llm(llm, "my-model.safetensors", resources, "My Model")
    assert path.name == "my_model_ai.json"
    assert len(llm.prompts) == 2
    # 두 번째 프롬프트에는 1차 실패 사유가 피드백된다.
    assert "필수 노드" in llm.prompts[1]
    assert wf.validate_workflow(path, model_file="my-model.safetensors") == []


def test_generate_with_llm_raises_after_retries(tmp_path):
    resources = _template(tmp_path)
    llm = _StubLLM([{"1": {"class_type": "SaveImage", "inputs": {}}} for _ in range(2)])
    with pytest.raises(RuntimeError):
        wf.generate_with_llm(llm, "my.safetensors", resources, "m", retries=2)


def test_generate_with_llm_rejects_placeholder_only_result(tmp_path):
    # 템플릿을 그대로 돌려주는(체크포인트 미지정) 응답은 채택하지 않는다.
    resources = _template(tmp_path)
    template = json.loads((resources / wf.TEMPLATE_FILENAME).read_text(encoding="utf-8"))
    llm = _StubLLM([template for _ in range(2)])
    with pytest.raises(RuntimeError):
        wf.generate_with_llm(llm, "my.safetensors", resources, "m", retries=2)


def test_workflow_file_name_follows_model_file(tmp_path):
    resources = _template(tmp_path)
    path = wf.build_from_template("models/ERNIE-AIO-Turbo-fp8.safetensors", "custom_model", resources)
    assert path.name == "ernie_aio_turbo_fp8.json"


def test_to_config_path_prefers_relative_and_falls_back(tmp_path):
    inside = tmp_path / "resources" / "a.json"
    assert wf.to_config_path(inside, tmp_path) == "resources/a.json"
    outside = tmp_path.parent / "outside.json"
    assert Path(wf.to_config_path(outside, tmp_path)).is_absolute()


def test_build_service_autocreates_missing_workflow(tmp_path):
    """워크플로우가 비어 있는 프로필이어도 앱 서비스 조립 시 템플릿으로 자동 생성된다."""
    import app as app_module
    from studio.settings.settings_manager import SettingsManager

    resources = _template(tmp_path / "resources")
    manager = SettingsManager(path=str(resources / "config.json"))
    manager.data["image_models"] = [{
        "id": "new_model", "name": "New", "model_file": "brand-new.safetensors", "workflow": "",
        "width": 512, "height": 512, "steps": 20, "cfg": 4.0, "sampler": "euler_ancestral",
        "scheduler": "beta", "negative_prompt": "", "stage2_workflow": "",
    }]
    manager.data["image_model"] = "new_model"
    manager.save()

    service = app_module.build_service(SettingsManager(path=str(resources / "config.json")))
    workflow_path = Path(getattr(service.workflow, "path", ""))
    assert workflow_path.is_file(), "워크플로우가 자동 생성되어야 한다"
    data = json.loads(workflow_path.read_text(encoding="utf-8"))
    ckpts = [n["inputs"]["ckpt_name"] for n in data.values() if n.get("class_type") == "CheckpointLoaderSimple"]
    assert ckpts == ["brand-new.safetensors"]
    stage2_path = Path(getattr(service.workflow, "stage2_path", "") or "")
    assert stage2_path.is_file(), "대사 합성 워크플로우도 템플릿에서 자동 생성되어야 한다"
    assert stage2_path.name == "brand_new_stage2.json"


def test_settings_window_autocreates_workflow_when_model_file_chosen(tmp_path):
    from studio.settings.settings_manager import SettingsManager
    from studio.settings.settings_window import SettingsWindow

    QApplication.instance() or QApplication([])
    resources = _template(tmp_path / "resources")
    manager = SettingsManager(path=str(resources / "config.json"))
    window = SettingsWindow(manager, lambda values: None, lambda values: None)
    try:
        window.form.imageModelFileEdit.setText("new-model.safetensors")
        window.form.imageModelWorkflowEdit.setText("")
        window._autocreate_workflow("new-model.safetensors")

        value = window.form.imageModelWorkflowEdit.text()
        assert value.endswith(".json")
        assert Path(manager.resolve_path(value)).is_file()
        # 테스트의 comfy_factory 는 None 을 돌려주므로 ComfyUI 확인은 "확인 불가"가 되지만,
        # 구조 검사는 통과해야 한다.
        assert "검사 통과" in window.workflowStatusLabel.text()
        assert window.aiWorkflowButton.text().startswith("AI로")
    finally:
        window.form.close()

