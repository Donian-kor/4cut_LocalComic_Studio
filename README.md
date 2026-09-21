# 4Cut Local Comic Studio v3

아이디어 하나를 입력하면 LM Studio가 4컷 스토리/대사/이미지 프롬프트를 만들고, ComfyUI가 4장의 이미지를 생성한 뒤 최종 2x2 만화로 합성합니다.

## v3에서 수정된 핵심

- 설정창을 독립적인 Qt Designer `QDialog`로 안정화
- 설정창에서 **적용**한 LM Studio / ComfyUI / 일반 설정을 다음 생성부터 즉시 반영
- 취소를 누르면 ComfyUI `/interrupt` 요청
- 생성마다 별도 폴더 생성 → 이전 만화 덮어쓰기 방지
- LM Studio 응답이 정확히 4컷인지 검증하고, 잘못된 응답은 1회 재요청
- 빈 패널을 자동으로 만들어 진행하지 않음
- ComfyUI `prompt_id` 및 workflow 오류 메시지 개선
- 상대 경로를 프로그램 폴더 기준으로 처리
- 한글 폰트 자동 탐색 및 말풍선 자동 줄바꿈
- 완성 미리보기 크기 변경 시 자동 재조정
- 생성 실패 시 오류 메시지 표시
- 빈 아이디어 생성 방지
- `run.bat`이 `.venv`를 자동 생성하고 의존성을 설치하도록 개선

## 실행

Windows에서는 `run.bat`을 실행하세요.

수동 실행:

```text
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Python 3.10 이상을 권장합니다.

## LM Studio

LM Studio에서 Local Server를 실행한 후 설정 메뉴에서:

- Host: `127.0.0.1`
- Port: `1234`
- API Path: `/v1`
- Model: LM Studio에 실제 로드한 모델명

을 입력합니다.

먼저 **연결 테스트**가 성공하는지 확인하세요.

## ComfyUI

ComfyUI를 실행한 후 설정 메뉴에서:

- Host: `127.0.0.1`
- Port: `8188`
- Workflow: `workflows/4cut_default.json`

을 지정합니다.

기본 workflow의:

```text
YOUR_MODEL.safetensors
```

를 실제 ComfyUI 체크포인트 파일명으로 바꾸거나, 자신의 API workflow JSON을 지정하세요.

기본 workflow는 다음 노드를 전제로 합니다.

- CLIPTextEncode: positive prompt
- KSampler: seed
- EmptyLatentImage: width / height
- SaveImage: 최종 이미지

다른 workflow를 사용할 경우 해당 workflow 구조에 맞게 `integrations/comfyui/workflow.py`를 조정해야 합니다.

## 설정 메뉴

`설정 → AI 연결 설정`

### LM Studio

- 서버 주소
- 포트
- API 경로
- 모델
- 연결 테스트

### ComfyUI

- 서버 주소
- 포트
- Workflow JSON
- 연결 테스트

### 일반

- 프로젝트 저장 위치
- 이미지 너비/높이
- 결과 자동 저장

설정은 `config/config.json`에 저장됩니다.

## 결과 저장

자동 저장이 켜져 있으면:

```text
projects/
└── 2026-09-21_091530_123/
    ├── panel_1.png
    ├── panel_2.png
    ├── panel_3.png
    ├── panel_4.png
    └── final_4cut.png
```

처럼 생성별로 분리됩니다.

자동 저장을 끄면 임시 결과가 `projects/.cache/` 아래에 생성되고, UI의 **저장** 버튼으로 원하는 위치에 PNG를 복사할 수 있습니다.

## Qt Designer

UI는 `.ui` 파일이 원본입니다.

```text
ui/main/main_window.ui
ui/idea/idea_section.ui
ui/generation/generation_section.ui
ui/preview/preview_section.ui
ui/result/result_section.ui
ui/settings/settings_window.ui
```

Python 코드가 `.ui`를 런타임에 로드하므로 Qt Designer에서 화면을 수정한 뒤 Python 코드를 다시 생성할 필요가 없습니다.
