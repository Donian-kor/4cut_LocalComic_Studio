# -*- coding: utf-8 -*-
"""디자인 토큰 단일 소스.

색상·폰트·라디우스 값을 이 모듈에서만 정의하고, 각 화면은 $FONT_STACK 형태의
QSS 템플릿을 render()로 치환해 사용한다. 색을 바꾸려면 여기만 고치면 된다.

- 악센트는 코랄 한 가지이며, 상태색은 성공/경고/오류 각 1종만 쓴다.
- 배경은 순검정이 아니라 붉은 기가 도는 웜 그레이 계열이다.
- UI 폰트는 사용자가 설정에서 선택하며(apply_font), 기본값은 Malgun Gothic이다.
"""
from string import Template

from PySide6.QtGui import QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect

# --- 표면 (웜 그레이 스케일) ---
BG = "#100e0d"
SURFACE = "#171412"
SURFACE_RAISED = "#1d1917"
SURFACE_HOVER = "#262120"
SURFACE_INPUT = "#221d1b"
BORDER = "#2e2825"
BORDER_STRONG = "#3c342f"
BORDER_HOVER = "#4b4139"

# --- 텍스트 ---
TEXT = "#f7f3f0"
TEXT_MUTED = "#c4b9b1"
TEXT_DIM = "#8d8279"
TEXT_FAINT = "#6b625c"

# --- 악센트 (코랄 단일) ---
ACCENT = "#e87e60"
ACCENT_HOVER = "#f18b6d"
ACCENT_PRESSED = "#d16c4f"
ACCENT_SOFT = "#3a221b"
ACCENT_SOFT_BORDER = "#7b4636"
ACCENT_SOFT_TEXT = "#f6b096"
ACCENT_TEXT = "#ef9a7d"
ACCENT_INK = "#1e1109"

# --- 상태 (각 1종) ---
SUCCESS = "#5ecb9a"
SUCCESS_TEXT = "#8fe0b8"
SUCCESS_SOFT = "#152c22"
SUCCESS_BORDER = "#2c5c45"

WARNING = "#e8b45a"
WARNING_TEXT = "#f0cd8b"
WARNING_SOFT = "#33280f"
WARNING_BORDER = "#6b5526"

DANGER = "#e0575f"
DANGER_TEXT = "#f19aa1"
DANGER_SOFT = "#3a1f22"
DANGER_BORDER = "#7d3d44"
DANGER_HOVER_BG = "#472529"

# --- 말풍선 ---
USER_BUBBLE = "#33221c"
USER_BUBBLE_BORDER = "#5c3b2e"

# --- 그림자 (배경 톤에 맞춘 웜 틴트) ---
SHADOW = "#0b0705"

# --- 라디우스 ---
RADIUS_SM = "8px"
RADIUS_MD = "12px"
RADIUS_LG = "16px"

# --- 폰트 ---
DEFAULT_FONT_FAMILY = "Malgun Gothic"
FALLBACK_FONT_STACK = "`'Malgun Gothic`', `'Noto Sans KR`', sans-serif"
MONO_STACK = "`'Consolas`', `'Cascadia Mono`', `'Malgun Gothic`', monospace"

_FONT_FAMILY = None
_FONT_STACK = None


def apply_font(family):
    """UI 폰트 가족을 설정한다. None이면 시스템 기본 폰트를 사용한다.

    app.py 시작 시와 설정 Apply 시 호출한다.
    """
    global _FONT_FAMILY, _FONT_STACK
    _FONT_FAMILY = family
    _FONT_STACK = None  # 다음 load_fonts() 호출에서 재계산
    if QApplication.instance() is not None:
        if family is None:
            QApplication.setFont(QFont())
        else:
            QApplication.setFont(QFont(family))


def load_fonts():
    """apply_font()로 설정된 UI 폰트를 바탕으로 QSS용 폰트 스택을 계산해 반환한다."""
    global _FONT_STACK
    if _FONT_STACK is not None:
        return _FONT_STACK
    if QApplication.instance() is None:
        _FONT_STACK = FALLBACK_FONT_STACK
        return _FONT_STACK
    if _FONT_FAMILY is not None:
        _FONT_STACK = f"`'{_FONT_FAMILY}`', {FALLBACK_FONT_STACK}"
    else:
        _FONT_STACK = FALLBACK_FONT_STACK
    return _FONT_STACK


def font_stack():
    load_fonts()
    return _FONT_STACK


def tokens():
    """$FONT_STACK 치환에 쓸 토큰 사전을 만든다."""
    data = {
        name: value
        for name, value in globals().items()
        if name.isupper() and isinstance(value, str)
    }
    data["FONT_STACK"] = font_stack()
    return data


def render(template):
    """$토큰 형태의 QSS 템플릿을 실제 값으로 치환한다."""
    return Template(template).substitute(tokens())


def _system_font_families():
    """시스템에서 사용할 수 있는 UI 폰트 가족 목록을 반환한다."""
    if QApplication.instance() is None:
        return []
    all_families = QFontDatabase.families()
    korean_keywords = (
        "고딕", "돋움", "굴림", "바탕", "명조", "체",
        "Gothic", "Dotum", "Gulim", "Batang", "Myeongjo", "Mincho",
        "Malgun", "맑은", "Apple SD", "Noto Sans", "Noto Serif", "Nanum", "나눔",
        "CJK", "Source Han", "본고딕", "본명조", "RIDIBatang", "리디"
    )
    preferred_head = (
        "Malgun Gothic", "맑은 고딕", "Noto Sans KR", "Noto Sans CJK KR",
        "Apple SD Gothic Neo", "나눔고딕", "NanumGothic", "본고딕", "Source Han Sans",
    )
    seen, matched, rest = set(), [], []
    for f in all_families:
        if f in seen:
            continue
        seen.add(f)
        if any(k in f for k in korean_keywords):
            matched.append(f)
        else:
            rest.append(f)
    head = [f for f in preferred_head if f in matched] + [f for f in sorted(matched) if f not in preferred_head]
    return head + sorted(rest)


def apply_shadow(widget, blur=26, offset_y=6, alpha=90, color=SHADOW):
    """배경 톤에 맞춘 부드러운 그림자를 위젯에 적용한다.

    QSS에는 box-shadow가 없으므로 QGraphicsDropShadowEffect를 사용한다.
    """
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, offset_y)
    shadow_color = QColor(color)
    shadow_color.setAlpha(alpha)
    effect.setColor(shadow_color)
    widget.setGraphicsEffect(effect)
    return effect
