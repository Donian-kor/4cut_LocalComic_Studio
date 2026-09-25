"""이미지 모델용 ComfyUI 워크플로우 자동 생성·검증 도우미.

- 모델 파일만 고르면 기본 템플릿(SD1.5 계열 API 골격)을 복사해 체크포인트명을 주입한다.
- 만들어진 워크플로우는 필수 노드/체크포인트 참조를 검사해 사용 가능 여부를 알려준다.
- 템플릿으로 커버되지 않는 모델 계열은 LM Studio(실험적)로 새 워크플로우를 만들고,
  검증을 통과한 결과만 파일로 저장한다. 실패하면 기존 워크플로우를 그대로 유지한다.
"""
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

TEMPLATE_FILENAME = "4cut_default.json"
DEFAULT_MODEL_PLACEHOLDER = "YOUR_MODEL.safetensors"
CHECKPOINT_NODE_TYPE = "CheckpointLoaderSimple"
CHECKPOINT_INPUT_NAME = "ckpt_name"
REQUIRED_NODE_TYPES = ("CheckpointLoaderSimple", "CLIPTextEncode", "KSampler", "SaveImage")

SYSTEM_PROMPT = (
    "당신은 ComfyUI API 워크플로우(노드 ID → {class_type, inputs} 사전)를 작성하는 도우미입니다. "
    "반드시 JSON 객체 하나만 반환하고, 노드 ID는 문자열, 각 노드는 class_type과 inputs를 가진 객체여야 합니다. "
    "존재하지 않는 노드 이름을 새로 만들지 말고, 참조 워크플로우에 있는 노드 구성만 사용하세요."
)


def slugify(value) -> str:
    """프로필 id·파일명으로 쓸 수 있는 안전한 문자열을 만든다."""
    cleaned = re.sub(r"[^0-9a-zA-Z가-힣]+", "_", str(value or "").strip()).strip("_").lower()
    return cleaned or "custom_model"


def workflow_stem(model_file, model_id="") -> str:
    """자동 생성 워크플로우 파일명의 뿌리를 만든다(모델 파일명 우선)."""
    stem = Path(str(model_file or "")).stem.strip()
    return slugify(stem or model_id)


def to_config_path(path, base_dir=None) -> str:
    """설정에 저장할 경로 문자열을 만든다(가능하면 base_dir 기준 상대경로)."""
    path = Path(path)
    if base_dir:
        try:
            return str(path.relative_to(Path(base_dir))).replace("\\", "/")
        except ValueError:
            pass
    return str(path)


def template_path(resources_dir, template_name=TEMPLATE_FILENAME) -> Path:
    return Path(resources_dir) / template_name


def load_workflow(path) -> dict:
    """워크플로우 JSON을 읽는다. 없거나 형식이 틀리면 예외를 올린다."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"워크플로우 파일이 없습니다: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"워크플로우 JSON 형식이 올바르지 않습니다: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("워크플로우 JSON 최상위가 객체(노드 사전)가 아닙니다.")
    return data


def _set_checkpoint(data: dict, model_file: str) -> bool:
    changed = False
    for node in data.values():
        if isinstance(node, dict) and node.get("class_type") == CHECKPOINT_NODE_TYPE:
            node.setdefault("inputs", {})[CHECKPOINT_INPUT_NAME] = model_file
            changed = True
    return changed


def build_from_template(model_file, model_id, resources_dir, template_name=TEMPLATE_FILENAME) -> Path:
    """기본 템플릿을 복사해 체크포인트명만 새 모델로 바꾼 워크플로우를 만든다."""
    model_file = str(model_file or "").strip()
    if not model_file:
        raise ValueError("모델 파일명이 비어 있습니다.")
    src = template_path(resources_dir, template_name)
    data = load_workflow(src)
    if not _set_checkpoint(data, model_file):
        raise ValueError(f"템플릿({src.name})에 {CHECKPOINT_NODE_TYPE} 노드가 없어 자동 생성할 수 없습니다.")
    target = Path(resources_dir) / f"{workflow_stem(model_file, model_id)}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _first_node(data: dict, class_type: str):
    for node in data.values():
        if isinstance(node, dict) and node.get("class_type") == class_type:
            return node
    return None


def _has_node_ref(node: dict, key: str, data: dict) -> bool:
    ref = (node.get("inputs") or {}).get(key)
    return isinstance(ref, list) and bool(ref) and str(ref[0]) in data


def validate_workflow(source, model_file="") -> list[str]:
    """워크플로우가 이 프로그램에서 실행 가능한지 검사하고 문제 목록을 돌려준다(정상이면 빈 목록)."""
    try:
        data = source if isinstance(source, dict) else load_workflow(source)
    except (OSError, ValueError) as e:
        return [str(e)]

    broken = [key for key, node in data.items() if not isinstance(node, dict)]
    if broken:
        return [f"노드 {', '.join(str(k) for k in broken)} 형식이 올바르지 않습니다."]

    errors = []
    classes = {node.get("class_type") for node in data.values()}
    for needed in REQUIRED_NODE_TYPES:
        if needed not in classes:
            errors.append(f"필수 노드가 없습니다: {needed}")

    for node in data.values():
        if node.get("class_type") != CHECKPOINT_NODE_TYPE:
            continue
        value = str((node.get("inputs") or {}).get(CHECKPOINT_INPUT_NAME) or "").strip()
        if not value or DEFAULT_MODEL_PLACEHOLDER in value:
            errors.append("체크포인트(모델 파일)가 워크플로우에 지정되지 않았습니다.")
            break
        if model_file and Path(value).name.lower() != Path(str(model_file)).name.lower():
            errors.append(f"워크플로우 체크포인트({value})가 선택한 모델({model_file})과 다릅니다.")
            break

    sampler = _first_node(data, "KSampler")
    if sampler is not None and not _has_node_ref(sampler, "positive", data):
        errors.append("KSampler의 positive 프롬프트 연결을 찾을 수 없습니다.")
    return errors


def validate_runnable(path, profile) -> list[str]:
    """WorkflowAdapter로 실제 조립(prepare)까지 해 보고 실패 사유를 돌려준다."""
    from studio.integrations.workflow import WorkflowAdapter
    try:
        WorkflowAdapter(path, profile=profile).prepare("validation prompt", seed=1)
    except Exception as e:  # 파일 없음/노드 누락 등 모두 사용자 안내 문구로 변환한다.
        return [f"워크플로우 조립 실패: {e}"]
    return []


def check_model_file(client, model_file, timeout=5):
    """ComfyUI가 해당 체크포인트를 갖고 있는지 확인한다. (상태, 안내문) 을 돌려준다.

    상태는 "ok"(있음) / "missing"(없음) / "unknown"(확인 불가) 중 하나다.
    """
    model_file = str(model_file or "").strip()
    if not model_file:
        return "unknown", "모델 파일이 지정되지 않았습니다."
    try:
        names = client.list_checkpoints(timeout=timeout)
    except Exception as e:
        return "unknown", f"ComfyUI 확인 불가: {e}"
    if not names:
        return "unknown", "ComfyUI가 체크포인트 목록을 반환하지 않았습니다."
    target = Path(model_file).name.lower()
    if any(Path(str(name)).name.lower() == target for name in names):
        return "ok", f"ComfyUI에 {model_file} 있음"
    return "missing", f"ComfyUI에 {model_file} 없음 — ComfyUI의 checkpoints 폴더에 파일을 넣어 주세요."


def build_llm_prompt(model_file, base_template=None, previous_errors=None) -> str:
    """LM Studio에 보낼 워크플로우 생성 프롬프트를 만든다."""
    lines = [
        f"이미지 생성 모델 파일: {model_file}",
        "아래 참조 워크플로우와 같은 노드 구성/연결을 유지하면서, 이 모델로 4컷 만화 이미지를 생성하는 ComfyUI API 워크플로우 JSON을 만들어 주세요.",
        f"- {CHECKPOINT_NODE_TYPE}의 inputs.{CHECKPOINT_INPUT_NAME} 값은 정확히 '{model_file}' 로 지정합니다.",
        "- 긍정/부정 CLIPTextEncode 2개, KSampler(seed/steps/cfg/sampler_name/scheduler), EmptyLatentImage(width/height), VAEDecode, SaveImage를 포함합니다.",
        "- 대사(말풍선 텍스트)는 넣지 않습니다. 이미지 생성만 담당합니다.",
        "참조 워크플로우 JSON:",
        json.dumps(base_template, ensure_ascii=False, indent=2) if base_template else "(참조 없음 — 표준 ComfyUI 이미지 생성 구성을 사용하세요.)",
    ]
    if previous_errors:
        lines.append("이전 시도의 문제점(반드시 고칠 것):")
        lines.extend(f"- {error}" for error in previous_errors)
    return "\n".join(lines)


def generate_with_llm(lm_client, model_file, resources_dir, model_id, template_name=TEMPLATE_FILENAME,
                      retries=3, output_suffix="_ai") -> Path:
    """LM Studio에 워크플로우 생성을 요청하고, 검증을 통과한 결과만 파일로 저장한다."""
    model_file = str(model_file or "").strip()
    if not model_file:
        raise ValueError("모델 파일명이 비어 있습니다.")
    try:
        base_template = load_workflow(template_path(resources_dir, template_name))
    except (OSError, ValueError):
        base_template = None

    errors = []
    for attempt in range(1, max(1, int(retries)) + 1):
        data = lm_client.chat_json(SYSTEM_PROMPT, build_llm_prompt(model_file, base_template, errors or None))
        errors = validate_workflow(data, model_file=model_file)
        if not errors:
            target = Path(resources_dir) / f"{workflow_stem(model_file, model_id)}{output_suffix}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return target
        logger.warning("AI 워크플로우 %s차 시도 실패: %s", attempt, errors)
    raise RuntimeError("AI가 만든 워크플로우가 검증을 통과하지 못했습니다 — " + " / ".join(errors))

