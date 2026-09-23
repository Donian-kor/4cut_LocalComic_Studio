# 4Cut Local Comic Studio

## 현재 버전

**v1.0**

4cut Local Comic Studio는 LM Studio를 스토리/대사 생성용 로컬 LLM으로 사용하고, ComfyUI를 이미지 생성 엔진으로 사용하는 로컬 4컷 만화 제작 프로그램입니다. 현재 기준본은 채팅형 UI와 순차 컷 생성, 개별 컷 재생성, 컷 간 생성 일관성 유지, 세션 저장/복원을 하나의 흐름으로 통합합니다. UI는 단일 테마 토큰(ui/theme.py) 기반의 웜 그레이 + 코랄 악센트 디자인이며, UI 폰트는 설정에서 고를 수 있습니다(기본값 Malgun Gothic).

## 핵심 기능

- 채팅형 UI와 세션 히스토리
- 분위기/그림체 선택
- LM Studio 기반 4컷 스토리/대사/이미지 프롬프트 생성
- ComfyUI 기반 컷 이미지 생성
- 이미지 + 대사 합성 후 1~4컷 순차 표시
- 생성 카드 테두리 펄스/글로우 애니메이션
- 생성 취소
- 전체 4컷 다시 만들기
- 개별 컷 다시 만들기 / 개별 컷 수정
- 개별 컷 변경 후 최종 4컷 자동 재합성
- 생성 중 세션 삭제/이름 변경 차단
- 세션 JSON 저장/복원
- 단일 테마 토큰(ui/theme.py) 기반 UI(웜 그레이 + 코랄 악센트, 상태색 각 1종, 카드 그림자, 커스텀 스크롤바)
- 설정 - 일반 탭에서 UI 폰트 선택
- 전송 버튼 연필 아이콘(assets/icons/send_pen.svg)
- 프로그램 버전 표기 `v1.0` 기준 관리

## UI 기준

- 테마는 ui/theme.py의 단일 토큰(색상-폰트-라디우스-그림자)에서 관리한다. 배경은 웜 그레이 계열, 악센트는 코랄 단일(#e87e60), 상태색은 성공-경고-오류 각 1종만 쓴다.
- 사용자 말풍선은 #33221c, AI 말풍선은 #171412를 쓴다. 카드에는 배경 톤에 맞춘 웜 틴트 그림자를 쓴다.
- UI 폰트는 설정 - 일반 탭의 UI 폰트 콤보에서 고른다. 기본값은 Malgun Gothic이다.
- 전송 버튼은 연필 아이콘(assets/icons/send_pen.svg) 버튼이며, 생성 중에는 ... 표시로 바뀐다.
- 하단 Composer는 기본 최대 2줄 높이를 유지하고 입력량이 늘어나면 내부 세로 스크롤을 사용합니다.
- 메인 우측 상단에는 중복 설정 버튼을 두지 않고 사이드바의 설정 버튼만 사용합니다.
- AI 작업 상태 라벨은 일반 상태보다 크게 표시하며 생성 중에는 작업 상태, 생성 완료 후에는 녹색 `● 생성 완료` 상태로 표시합니다.
- 스토리/컷 생성 정보와 결과는 채팅 메시지 흐름에 맞춰 표시합니다.

## 생성 일관성 정책

한 만화가 시작되면 다음 생성 컨텍스트를 1회 확정하고 1~4컷에 공유합니다.

```text
ComicGenerationContext
├─ master_seed
├─ character_prompt
├─ style_prompt
├─ model
├─ width / height
├─ steps
├─ cfg
├─ sampler
├─ scheduler
└─ negative_prompt
```

캐릭터 외형 프롬프트와 스타일 프롬프트는 하드코딩하지 않습니다. 사용자가 선택한 분위기/그림체와 LM Studio가 만든 해당 만화의 캐릭터 정보를 바탕으로 생성 시 한 번 확정하고 모든 컷에서 재사용합니다.

일반 생성에서는 1개의 Master Seed를 모든 컷에 공유합니다. 개별 컷 재생성에서는 전체 만화의 생성 설정과 공통 프롬프트를 유지하면서 재생성 대상 컷만 새 revision seed를 사용합니다.

## 배경 유지 정책

각 컷의 배경은 LM Studio가 만든 해당 컷의 장면/이미지 프롬프트를 기준으로 유지합니다. 배경을 자세하게 묘사할 필요는 없지만, 장면을 확인할 수 있는 환경 정보가 프롬프트에 남아 있어야 하며 임의로 빈 배경이나 순백색 배경으로 대체하지 않습니다.

단, 스토리에서 흰색 벽/흰색 공간/눈밭 등 흰색 배경을 명시적으로 요구하는 경우에는 그 내용을 유지합니다.

## 생성 흐름

```text
사용자 아이디어
  ↓
LM Studio 스토리 계획
  ↓
Character Prompt / Style Prompt / Master Seed 확정
  ↓
1컷 생성 → 대사 합성 → 1컷 표시
  ↓
2컷 생성 → 대사 합성 → 2컷 표시
  ↓
3컷 생성 → 대사 합성 → 3컷 표시
  ↓
4컷 생성 → 대사 합성 → 4컷 표시
  ↓
최종 2×2 합성
```

## 개별 컷 재생성

완성된 각 컷에는 다음 액션을 제공합니다.

```text
↻ 이 컷 다시 만들기
✎ 이 컷 수정
```

개별 재생성은 전체 스토리 생성이나 다른 컷의 이미지 생성은 다시 실행하지 않습니다. 기존 Comic 계획의 장면/캐릭터/스타일/모델 설정을 재사용하고 선택된 컷만 새 revision seed로 생성합니다.

재생성 완료 후 최종 4컷 합성은 자동으로 다시 실행합니다. 결과가 마음에 들지 않으면 같은 컷을 다시 재생성할 수 있습니다.

## 생성 중 세션 정책

세션 상태가 `generating`이면:

- 사이드바 삭제 버튼 비활성화
- 이름 변경 비활성화
- 삭제 로직에서도 생성 중 세션 삭제 거부

생성 완료/실패/취소 상태가 되면 다시 삭제할 수 있습니다.

## 모델 관리

`설정 → 이미지 모델`에서 모델 프로필을 관리합니다. 모델 프로필에는 다음 정보가 포함됩니다.

- 모델 ID / 이름
- ComfyUI 모델 파일
- Workflow JSON
- 해상도
- Steps / CFG
- Sampler / Scheduler
- Negative Prompt

패널 재생성은 해당 세션이 처음 생성될 때 사용했던 생성 설정을 우선 유지합니다.

## 프로그램 정보

- 프로그램명: **4cut Local Comic Studio**
- 테마: `ui/theme.py` 단일 토큰(웜 그레이 + 코랄 악센트, 상태색 각 1종)
- 현재 버전: **v1.0**
- UI 프레임워크: PySide6
- 스토리/대사: LM Studio Local Server
- 이미지 생성: ComfyUI API
- 저장 위치: `projects/`
- 세션 인덱스: `projects/.sessions/sessions.json`

## 파일 구조 주요 항목

```text
app.py
app/version.py
app/main_controller.py
ui/theme.py
ui/main/main_window.py
ui/chat/chat_widgets.py
ui/generation/generation_section.py
ui/idea/idea_section.py
ui/preview/preview_section.py
ui/result/result_section.py
settings/settings_window.py
settings/settings_manager.py
settings/model_manager.py
tests/
assets/icons/send_pen.svg
core/models/comic.py
core/models/chat.py
core/services/story_service.py
core/services/comic_service.py
core/services/image_service.py
core/services/session_manager.py
core/workers/comic_worker.py
core/workers/panel_regeneration_worker.py
integrations/lmstudio/client.py
integrations/comfyui/client.py
integrations/comfyui/workflow.py
workflows/
projects/
디자인.md
```

## 세션 저장

중앙 인덱스는 `projects/.sessions/sessions.json`을 사용합니다. 완료된 프로젝트 폴더에도 `session.json`이 기록됩니다. 세션에는 대화 메시지와 함께 개별 컷 재생성에 필요한 Comic 계획, Character Prompt, Style Prompt, Master Seed, 생성 설정, 컷별 결과 경로를 저장합니다.

## 실행

```text
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

LM Studio Local Server와 ComfyUI가 실행되어 있어야 생성 기능을 사용할 수 있습니다.

## 버전 규칙 및 이력

프로그램 버전은 개발 단계에서는 `v0.1`, `v0.2`처럼 소수점 단위로 관리하고, 최초 정식 기준본을 `v1.0`으로 시작합니다. 이후 기능 추가는 `v1.1`, 호환성/수정 중심 변경은 `v1.0.x` 체계를 사용할 수 있습니다.

### v1.1 (테마-폰트-전송 버튼)
- 단일 테마 토큰(ui/theme.py) 기반 UI: 웜 그레이 배경, 코랄 악센트(#e87e60) 단일, 상태색 각 1종
- UI 폰트를 설정 - 일반 탭에서 선택(기본값 Malgun Gothic), 적용 버튼으로 즉시 반영
- 전송 버튼을 연필 아이콘(assets/icons/send_pen.svg)으로 변경, 생성 중 ... 표시
- 설정 적용 시 설정 값 저장 누락(manager.save) 수정

### v1.0
- 최종 기준본 재정립
- 채팅형 UI / 세션 / 순차 컷 생성 / 개별 컷 재생성 기능 통합
- Master Seed / Character Prompt / Style Prompt 기반 컷 간 일관성 유지
- 생성 중 세션 삭제/이름 변경 차단
- Composer 2줄 고정 + 내부 스크롤
- 메인 헤더 중복 설정 버튼 제거
- AI 작업 상태 표시 개선 및 생성 완료 녹색 상태
- 스토리 장면의 배경 유지 규칙 강화

### v0.2
- 채팅형 UI 전환 단계
- 컷별 순차 생성 및 생성 카드 애니메이션
- 개별 컷 재생성/수정과 최종 4컷 자동 재합성
- 세션 저장/복원 구조
- 만화 단위 생성 컨텍스트 공유

### v0.1
- 기본 4컷 스토리/이미지/대사 생성 파이프라인
- LM Studio 및 ComfyUI 연동
- 프로젝트 파일 저장 구조

## 디자인 문서

`디자인.md`에는 UI/UX 설계와 동작 기준만 기록합니다. 버전 정보와 프로젝트 전체 상태는 이 README를 기준으로 합니다.
