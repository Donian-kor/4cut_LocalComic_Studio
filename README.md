# 4Cut Local Comic Studio

## 현재 버전

**v1.2.2**

4cut Local Comic Studio는 LM Studio를 스토리/대사 생성용 로컬 LLM으로 사용하고, ComfyUI를 이미지 생성 엔진으로 사용하는 로컬 4컷 만화 제작 프로그램입니다. 현재 기준본은 채팅형 UI와 순차 컷 생성, 개별 컷 재생성, 컷 간 생성 일관성 유지, 세션 저장/복원을 하나의 흐름으로 통합합니다. UI는 단일 테마 토큰(studio/ui/theme.py) 기반의 웜 그레이 + 코랄 악센트 디자인이며, UI 폰트는 설정에서 고를 수 있습니다(기본값 Malgun Gothic).

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
- 단일 테마 토큰(studio/ui/theme.py) 기반 UI(웜 그레이 + 코랄 악센트, 상태색 각 1종, 카드 그림자, 커스텀 스크롤바)
- 설정 - 일반 탭에서 UI 폰트 선택
- 전송 버튼 연필 아이콘(resources/send_pen.svg)
- 프로그램 버전 표기 `v1.2.2` 기준 관리

## UI 기준

- 테마는 studio/ui/theme.py의 단일 토큰(색상-폰트-라디우스-그림자)에서 관리한다. 배경은 웜 그레이 계열, 악센트는 코랄 단일(#e87e60), 상태색은 성공-경고-오류 각 1종만 쓴다.
- 사용자 말풍선은 #33221c, AI 말풍선은 #171412를 쓴다. 카드에는 배경 톤에 맞춘 웜 틴트 그림자를 쓴다.
- UI 폰트는 설정 - 일반 탭의 UI 폰트 콤보에서 고른다. 기본값은 Malgun Gothic이다.
- 전송 버튼은 연필 아이콘(resources/send_pen.svg) 버튼이며, 생성 중에는 ... 표시로 바뀐다.
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

### 새 모델 추가 (워크플로우 자동 생성)

워크플로우 JSON을 직접 만들 줄 몰라도 모델을 추가할 수 있습니다.

1. `설정 → 이미지 모델 → ＋ 추가`로 프로필을 만든 뒤 **모델 파일(.safetensors)** 만 고릅니다.
2. 프로그램이 기본 템플릿(`resources/4cut_default.json`, SD1.5 계열 API 골격)을 복사해 `resources/<모델파일명>.json`을 자동 생성하고, 체크포인트 이름만 새 모델로 바꿔 넣습니다.
3. 곧바로 자동 검사 결과를 `워크플로우 도우미` 줄에 표시합니다.
   - 필수 노드(`CheckpointLoaderSimple`/`CLIPTextEncode`/`KSampler`/`SaveImage`) 존재
   - 체크포인트 지정 여부(템플릿 자리표시자 `YOUR_MODEL.safetensors` 거부)
   - `WorkflowAdapter.prepare()` 조립 드라이런 통과 여부
   - ComfyUI가 해당 체크포인트를 실제로 갖고 있는지(`/object_info/CheckpointLoaderSimple`)
4. `모델 정보 저장`은 위 검사를 모두 통과해야 저장됩니다(실패 시 저장 차단 + 사유 안내).

자동 생성이 맞지 않는 계열(Flux/SD3 등 노드 구조가 다른 모델)은 **`AI로 워크플로우 만들기 (실험적)`** 버튼을 씁니다.

- LM Studio 언어모델에게 참조 워크플로우와 실패 사유를 함께 보내 최대 3회 생성 요청합니다.
- 생성 결과는 같은 검사를 통과했을 때만 `resources/<모델파일명>_ai.json`으로 저장·적용되고, 실패하면 기존 워크플로우를 그대로 유지합니다.
- AI 서버 탭에 LM Studio 모델이 설정되어 있어야 하며, 생성은 백그라운드 스레드에서 돌아 UI가 멈추지 않습니다.

워크플로우가 비어 있는 프로필로 프로그램을 실행하면, 시작 시점에 템플릿으로 자동 생성을 한 번 더 시도합니다(마지막 안전망).

## 프로그램 정보

- 프로그램명: **4cut Local Comic Studio**
- 테마: `studio/ui/theme.py` 단일 토큰(웜 그레이 + 코랄 악센트, 상태색 각 1종)
- 현재 버전: **v1.3.0**
- UI 프레임워크: PySide6
- 스토리/대사: LM Studio Local Server
- 이미지 생성: ComfyUI API
- 저장 위치: `projects/`
- 세션 인덱스: `projects/.sessions/sessions.json`

## 파일 구조 주요 항목

```text
app.py
studio/__init__.py
studio/version.py
studio/main_controller.py
studio/models/comic.py
studio/models/chat.py
studio/models/image_model.py
studio/models/generation_state.py
studio/services/story_service.py
studio/services/comic_service.py
studio/services/image_service.py
studio/services/compose_service.py
studio/services/workflow_factory.py
studio/services/session_manager.py
studio/services/bubble_detector.py
studio/services/bubble.py
studio/services/layout.py
studio/workers/comic_worker.py
studio/workers/panel_regeneration_worker.py
studio/workers/server_status_worker.py
studio/integrations/lmstudio.py
studio/integrations/comfyui.py
studio/integrations/workflow.py
studio/settings/settings_window.py
studio/settings/settings_manager.py
studio/settings/model_manager.py
studio/ui/theme.py
studio/ui/main_window.py
studio/ui/main_window.qss
studio/ui/styles.py
studio/ui/chat_view_manager.py
studio/ui/chat_widgets.py
studio/ui/idea_section.py + idea_section.ui
studio/ui/composer.py + composer.ui
studio/ui/sidebar.py + sidebar.ui
studio/ui/empty_state.py + empty_state.ui
studio/ui/settings_window.ui
resources/config.json
resources/send_pen.svg
resources/*.json (ComfyUI workflow)
tests/
projects/
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

프로그램 버전은 개발 단계에서는 `v0.1`, `v0.2`처럼 소수점 단위로 관리하고, 최초 정식 기준본을 `v1.0`으로 시작합니다. 이후 기능 추가는 `v1.1`, `v1.2`처럼 소수점 단위로, 호환성/수정 중심 변경은 `v1.0.x` 체계를 사용할 수 있습니다.

### v1.3.0 (새 모델 추가 자동화 — 워크플로우 자동 생성/검증)
- `studio/services/workflow_factory.py` 신설: 모델 파일만 고르면 기본 템플릿(`resources/4cut_default.json`)을 복사해 체크포인트명을 주입한 워크플로우를 `resources/<모델파일명>.json`으로 생성
- 생성/저장 전 자동 검사: 필수 노드 존재, 자리표시자(`YOUR_MODEL.safetensors`) 거부, 체크포인트-모델명 일치, `KSampler.positive` 연결, `WorkflowAdapter.prepare()` 드라이런
- `ComfyUIClient.list_checkpoints()` 추가(`/object_info/CheckpointLoaderSimple`) → ComfyUI에 모델 파일이 실제로 있는지 확인(연결 안 되면 "확인 불가"로 구분)
- 설정창 `이미지 모델` 탭에 `워크플로우 도우미` 행 추가: 자동 생성 결과·검사 상태를 색으로 표시하고, 저장 시 검사 실패면 저장 차단 + 사유 안내
- `AI로 워크플로우 만들기 (실험적)` 버튼 추가: LM Studio에 워크플로우 생성을 요청(최대 3회, 실패 사유 피드백)하고 검증 통과분만 `resources/<모델파일명>_ai.json`으로 적용, 실패 시 기존 워크플로우 유지(백그라운드 스레드 실행)
- 앱 시작 시 워크플로우가 비어 있는 프로필이면 템플릿으로 자동 생성하는 안전망 추가(`app.py`)
- 회귀 테스트 추가: `tests/test_workflow_factory.py`(생성·검증·재시도·폴백·설정창 자동 생성), `tests/test_comfyui_client.py`(체크포인트 목록 파싱)

### v1.2.3 (헤더 제거 · 상태라벨 이동 · 채팅 영역 배차 수정)
- 창 안 상단 헤더(`headerFrame` + `logoLabel` 제목/버전) 제거 — 윈도우 타이틀바와 중복되던 제목 정리, 레이아웃이 64px 위로 올라와 채팅 영역 확대
- 윈도우 타이틀바(제목 표시줄)에는 프로그램 전체 이름과 버전을 표시: `4cut Local Comic Studio v1.2.3` (`APP_NAME` + `APP_VERSION` 자동 반영 — 버전 올리면 타이틀도 함께 갱신)
- 서버·생성 상태 라벨(`saveStatusLabel`)을 헤더에서 입력창 전송버튼 좌측으로 이동(`composer.ui`) — objectName 재사용으로 QSS 상태색(`done`/`busy`/`error` 등) 그대로 유지
- `set_empty_visible()`이 `emptyHost`/`chatHost` 컨테이너 자체도 토글하도록 수정 — 숨겨진 빈 상태 컨테이너가 stretch 절반을 차지해 채팅창이 반반으로 접히던 버그 수정, 초기 상태는 빈 화면만 표시
- 회귀 테스트 추가/보강: 헤더 제거·상태라벨 위치(`test_main_window_layout.py`), 빈화면/채팅 Host 토글, `composer.ui` 상태라벨 존재(`test_architecture_boundaries.py`)

### v1.2.2 (UI 배치 회귀 수정)
- `Sidebar`/`Composer`를 Host 레이아웃에 명시적 `addWidget`으로 배치 — parent만 지정해 레이아웃에서 누락되던 버그 수정(사이드바·입력창이 화면에 안 보이던 원인)
- `mainSplitter` 초기 `setSizes([260, 940])` + `setStretchFactor` 설정 — 사이드바 칸 0px 폭 회귀 방지, `sidebar` 최소폭 220px 보장
- `mainHost`의 `emptyHost`/`chatHost` stretch=1, `composerHost` stretch=0으로 세로 배분 명시
- 배치 회귀 방지 GUI smoke 테스트 추가(`tests/test_main_window_layout.py`): Host 레이아웃 진입 여부, 위젯 크기/가시성, splitter 초기 폭 검증

### v1.2.1 (안정화 — 리뷰 잔여 이슈 정리)
- 설정 기본값(`settings_manager.py` `DEFAULTS`)에 `art_style_prompt` 키 추가로 설정 키 누락 제거
- YOLO 말풍선 검출 stdout 파싱을 마지막 줄 단일 파싱에서 역순 JSON 스캔(+목록 타입 검증)으로 개선 — ultralytics 경고 로그가 섞여도 정상 검출 결과 유지
- 세션 재생성용 서비스 팩토리의 `except TypeError` 폴백을 호출 전 시그니처 검사로 교체 — 팩토리 내부 TypeError 마스킹 제거
- 생성 카드 `set_status`의 문구 기반 단계 파싱 제거: 진행 표시는 문구/진행바 갱신만 하고 단계 전환은 `panel_started`/`compose_started` 타입 신호 경로가 전담
- 워크플로우 `prepare`의 `dialogue` 인자와 호출부 유지(재검증 확인)

### v1.2 (UI-로직 분리 + 모듈 구조 통합)
- 단일 `studio/` 패키지 + `resources/` 구조로 통합: `app/`→`studio/`, `core/`→`studio/{models,services,workers}`, `compose/`→`studio/services` 흡수, `integrations/` 평탄화(`lmstudio.py`, `comfyui.py`, `workflow.py`), `settings/`→`studio/settings`, `ui/` 중간폴더 제거→`studio/ui/` 평탄화
- `config/`, `workflows/`, `assets/`를 `resources/`로 병합(config.json + workflow JSON + send_pen.svg), 기존 `config/config.json`은 첫 실행 시 1회성으로 `resources/config.json` 이관
- CI compileall 대상과 README 파일 구조를 새 구조로 갱신
- `ChatViewManager` 신규 추가: 채팅 스크롤 영역·빈 상태 위젯·생성/결과 카드 캐시를 캡슐화하고 `MainWindow`에서 직접 관리하던 `_generation_widgets`/`_result_widgets` 제거
- 사이드바·컴포지터·빈 상태를 UI 컴포넌트로 분리, QSS 템플릿을 `studio/ui/styles.py` + `main_window.qss`로 분리
- 사이드바 세션 목록을 전체 재생성 대신 증분 갱신하도록 변경(스크롤 위치·선택 상태 보존)
- 전송 버튼 `clicked` → `_submit` 시그널 연결 복구
- 이미지 해상도 기본값 768 → 512로 코드 전반 통일, `config.json`의 `font_path` 절대경로 제거(자동 탐색 사용)
- 설정 저장 임시파일을 UUID 이름으로 원자 교체(세션 저장 방식과 통일)
- Ruff lint 규칙에 `F`(미사용 import/변수) 추가, 미사용 import 제거
- ComfyUI 완료/오류 메시지 판정 조건 병합(`wait_for_image`)
- 세션 삭제 후 사이드바 즉시 갱신(`_refresh_sidebar`), 2단계 합성 `stage2_workflow` 필드 추가

### v1.1 (테마-폰트-전송 버튼)
- 단일 테마 토큰(studio/ui/theme.py) 기반 UI: 웜 그레이 배경, 코랄 악센트(#e87e60) 단일, 상태색 각 1종
- UI 폰트를 설정 - 일반 탭에서 선택(기본값 Malgun Gothic), 적용 버튼으로 즉시 반영
- 전송 버튼을 연필 아이콘(resources/send_pen.svg)으로 변경, 생성 중 ... 표시
- 설정 적용 시 설정 값 저장 누락(manager.save) 수정
- Qt Designer 기반 UI 파일(main_window.ui, settings_window_ui.py) 제거, UI 정의를 코드 기반으로 마이그레이션

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
