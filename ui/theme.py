# -*- coding: utf-8 -*-
"""디자인 토큰 단일 소스.

색상·폰트·라디우스 값을 이 모듈에서만 정의하고, 각 화면은 $TOKEN 형태의
QSS 템플릿을 `render()`로 치환해 사용한다. 색을 바꾸려면 여기만 고치면 된다.

- 악센트는 코랄 한 가지이며, 상태색은 성공/경고/오류 각 1종만 쓴다.
- 배경은 순검정이 아니라 붉은 기가 도는 웜 그레이 계열이다.
"""
from pathlib import Path
from string import Template

from PySide6.QtGui import QColor, QFontDatabase
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

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

FONT_NAME = "Pretendard"
FALLBACK_FONT_NAME = "Malgun Gothic"
MONO_STACK = "'Consolas', 'Cascadia Mono', 'Malgun Gothic', monospace"

_FONT_STACK = None


def load_fonts() -> str:
    """번들된 Pretendard를 등록하고 본문에 사용할 family 이름을 돌려준다.

    QApplication이 없거나 폰트 파일이 없으면 시스템 폰트로 폴백한다.
    """
    global _FONT_STACK
    if _FONT_STACK is not None:
        return FONT_NAME if FONT_NAME in _FONT_STACK else FALLBACK_FONT_NAME

    families = []
    if QApplication.instance() is not None and FONT_DIR.exists():
        for path in sorted(FONT_DIR.glob("Pretendard-*.otf")):
            font_id = QFontDatabase.addApplicationFont(str(path))
            if font_id != -1:
                families.extend(QFontDatabase.applicationFontFamilies(font_id))

    if FONT_NAME in families:
        _FONT_STACK = f"'{FONT_NAME}', '{FALLBACK_FONT_NAME}', sans-serif"
    else:
        _FONT_STACK = f"'{FALLBACK_FONT_NAME}', 'Noto Sans KR', sans-serif"
    return FONT_NAME if FONT_NAME in families else FALLBACK_FONT_NAME


def font_stack() -> str:
    load_fonts()
    return _FONT_STACK


def tokens() -> dict:
    """$TOKEN 치환에 쓸 토큰 사전을 만든다."""
    data = {
        name: value
        for name, value in globals().items()
        if name.isupper() and isinstance(value, str)
    }
    data["FONT_STACK"] = font_stack()
    return data


def render(template: str) -> str:
    """$TOKEN 형태의 QSS 템플릿을 실제 값으로 치환한다."""
    return Template(template).substitute(tokens())


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
