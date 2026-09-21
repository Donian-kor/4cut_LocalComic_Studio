# 4Cut Local Comic Studio - Z-Anime Model Manager Edition

아이디어 하나를 입력하면 LM Studio가 4컷 스토리/대사/이미지 프롬프트를 만들고, 선택한 ComfyUI 이미지 모델이 4장의 이미지를 생성한 뒤 최종 2x2 만화로 합성합니다.

## 이번 버전의 핵심

- 기존 설정 메뉴의 동작은 유지
- **이미지 모델 관리자** 추가
- Z-Anime Base AIO FP8 프로필을 기본 등록
- Z-Anime 전용 API Workflow 추가
- 모델마다 Workflow / 모델 파일 / 해상도 / Steps / CFG / Sampler / Scheduler / Negative Prompt를 별도로 보관
- 생성 시 선택한 모델 프로필의 값을 Workflow에 자동 주입
- `4cut_default.json` 기존 Workflow는 삭제하거나 변경하지 않음
- 사용자 모델 추가/삭제/편집 가능
- 모델 선택을 바꾸면 다음 생성부터 선택 모델과 해당 Workflow가 사용됨

## 이미지 모델 설정

`설정 → 이미지 모델`에서 관리합니다.

### 기본 등록 모델

```text
Z-Anime Base AIO FP8
model_file:
z-anime-base-aio-fp8.safetensors

workflow:
workflows/z_anime_base_aio_fp8.json
```

현재 프로필은 Z-Anime Base 계열의 공식 Workflow 구성에 맞춘 AIO 체크포인트 방식입니다. AIO 모델은 `CheckpointLoaderSimple`에서 MODEL / CLIP / VAE를 한 번에 받아 Positive/Negative CLIPTextEncode → KSampler → VAEDecode → SaveImage 흐름으로 사용합니다.

기본 프로필의 초기 생성값은 768x768 / 28 steps / CFG 4.0 / euler_ancestral / beta입니다. 실제 생성 품질과 속도는 설치된 ComfyUI 버전, VRAM, 모델 상태에 따라 달라질 수 있습니다.

## 사용자 모델 추가

`설정 → 이미지 모델 → + 추가`에서 모델을 추가합니다.

입력해야 하는 값:

- 모델 이름
- ComfyUI에서 로드할 모델 파일명
- API 형식 Workflow JSON
- 해상도
- Steps
- CFG
- Sampler
- Scheduler
- Negative Prompt

모델 파일은 ComfyUI가 실제로 인식하는 체크포인트/모델 파일명을 입력하세요. Workflow는 해당 모델 구조에 맞는 **ComfyUI API Prompt JSON**이어야 합니다.

## 모델과 Workflow의 관계

4Cut Local은 모델 파일만 교체하지 않습니다.

```text
이미지 모델 선택
      ↓
ImageModelProfile
      ├─ model_file
      ├─ workflow
      ├─ width / height
      ├─ steps / cfg
      ├─ sampler / scheduler
      └─ negative_prompt
      ↓
WorkflowAdapter
      ↓
ComfyUI /prompt
      ↓
패널 이미지
```

따라서 모델별로 다른 노드 구조를 사용할 수 있도록 Workflow를 프로필에 묶어두었습니다.

## ComfyUI

ComfyUI 설정은 기존처럼:

- Host: `127.0.0.1`
- Port: `8188`

을 사용합니다.

`설정 → ComfyUI → 연결 테스트`로 서버 연결을 확인할 수 있습니다.

기존 `comfyui.workflow` 설정값은 호환성을 위해 남아 있지만, 이미지 모델 관리가 등록된 경우 실제 생성에는 **선택된 이미지 모델 프로필의 Workflow**가 사용됩니다.

## LM Studio

LM Studio에서 Local Server를 실행한 후 설정 메뉴에서:

- Host: `127.0.0.1`
- Port: `1234`
- API Path: `/v1`
- Model: LM Studio에 실제 로드한 모델명

을 입력합니다.

## 실행

Windows에서는 기존 프로젝트의 실행 방식대로 실행하세요.

```text
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

## Qt Designer

UI 원본은 `.ui` 파일입니다.

```text
ui/main/main_window.ui
ui/idea/idea_section.ui
ui/generation/generation_section.ui
ui/preview/preview_section.ui
ui/result/result_section.ui
ui/settings/settings_window.ui
```

이번 버전에서는 기존 설정창 구조를 유지하면서 `이미지 모델` 탭만 추가했습니다.
