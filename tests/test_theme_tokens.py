# -*- coding: utf-8 -*-
"""디자인 토큰과 QSS 템플릿이 온전히 치환되는지 검증한다.

토큰 누락(치환 안 된 $TOKEN)이나 이전 악센트 색이 남아 있으면 실패한다.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from settings.settings_window import SETTINGS_QSS_TEMPLATE
from ui import theme
from ui.main.main_window import MainWindow

# 스킬 감사에서 지적한 "AI 보라" 계열 — 하나도 남아 있으면 안 된다.
LEGACY_ACCENT_COLORS = ("#6366f1", "#818cf8", "#a5b4fc", "#c7cbff", "#4b50a2", "#242946", "#2a2f5d", "#7477f5")


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def test_tokens_have_no_placeholder_leftovers(qapp):
    for template in (MainWindow.QSS_TEMPLATE, SETTINGS_QSS_TEMPLATE):
        rendered = theme.render(template)
        assert "$" not in rendered
        assert theme.ACCENT in rendered
        assert "None" not in rendered


def test_legacy_ai_purple_is_removed(qapp):
    for template in (MainWindow.QSS_TEMPLATE, SETTINGS_QSS_TEMPLATE):
        rendered = theme.render(template).lower()
        for legacy in LEGACY_ACCENT_COLORS:
            assert legacy not in rendered, f"이전 악센트 색이 남아 있습니다: {legacy}"


def test_single_accent_and_one_color_per_status(qapp):
    # 악센트는 코랄 1종, 상태색은 성공/경고/오류 각 1종만 쓴다.
    assert theme.ACCENT == "#e87e60"
    assert theme.SUCCESS == "#5ecb9a"
    assert theme.WARNING == "#e8b45a"
    assert theme.DANGER == "#e0575f"


def test_bundled_pretendard_fonts_are_loaded(qapp):
    family = theme.load_fonts()
    assert family == "Pretendard"
    assert "Pretendard" in theme.font_stack()


def test_qss_renders_interactive_states(qapp):
    rendered = theme.render(MainWindow.QSS_TEMPLATE)
    # 스킬 Fix Priority 4: hover/pressed 상태가 실제로 존재해야 한다.
    assert "QPushButton#sendButton:hover" in rendered
    assert "QPushButton#sendButton:pressed" in rendered
    assert "QPushButton#newChatButton:hover" in rendered
    assert "QListWidget#sessionList::item:hover" in rendered
