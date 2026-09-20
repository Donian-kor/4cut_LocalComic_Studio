# 4Cut Local

사용자가 아이디어 하나를 입력하고 생성 버튼을 누르면:

1. LM Studio가 아이디어를 4컷 만화 구조로 확장
2. 캐릭터/스토리/대사/컷별 이미지 프롬프트 생성
3. ComfyUI에서 4장 이미지 생성
4. Pillow가 2x2 4컷으로 합성하고 대사 말풍선 추가
5. 완성된 PNG 저장

## 구조

- `ui/` : Qt Designer에서 직접 편집하는 UI
- `features/` : 화면 섹션별 동작
- `core/` : 데이터 모델/서비스/백그라운드 작업
- `integrations/` : LM Studio / ComfyUI 연결
- `settings/` : 설정창 및 설정 저장
- `compose/` : 4컷 레이아웃/말풍선
- `workflows/` : ComfyUI API workflow
- `projects/` : 결과 프로젝트

## 실행

Python 3.10+ 권장.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## 1) LM Studio

LM Studio에서 로컬 서버를 실행한 뒤 설정창에서:

- Host: `127.0.0.1`
- Port: `1234`
- API Path: `/v1`
- Model: 실제 로드한 모델명

을 입력하고 연결 테스트를 누릅니다.

## 2) ComfyUI

ComfyUI를 실행하고 설정창에서:

- Host: `127.0.0.1`
- Port: `8188`
- Workflow: `workflows/4cut_default.json`

을 지정합니다.

**중요:** 기본 workflow의 `YOUR_MODEL.safetensors`를 실제 Checkpoint 파일명으로 변경하거나, 자신의 ComfyUI API workflow를 `workflows/`에 넣어 사용하세요. 노드 구조가 다른 workflow라면 `integrations/comfyui/workflow.py`의 프롬프트/seed/크기 노드 ID를 맞춰야 합니다.

## Qt Designer

각 `.ui` 파일은 Qt Designer에서 독립적으로 수정할 수 있습니다.

- `ui/main/main_window.ui`
- `ui/idea/idea_section.ui`
- `ui/generation/generation_section.ui`
- `ui/preview/preview_section.ui`
- `ui/result/result_section.ui`
- `ui/settings/settings_window.ui`

메인 창은 각 섹션을 위한 placeholder에 Python으로 실제 section widget을 삽입합니다. 따라서 Designer에서 섹션 UI와 메인 배치를 따로 수정할 수 있습니다.

## 생성 취소

생성 중에는 `■ 생성 취소` 버튼이 표시됩니다.

- 현재 작업을 취소 요청
- ComfyUI에 실행 중인 prompt가 있으면 `/interrupt` 요청
- 이후 컷 생성 중단
- 완료된 임시 이미지와 상태는 유지
- 다시 생성할 수 있음

## 주의

이 프로젝트는 외부 AI 프로그램(LM Studio, ComfyUI)의 실제 설치/모델/workflow를 포함하지 않습니다.
