# -*- coding: utf-8 -*-
"""UI 폰트 선택 콤보가 설정창에 붙고, 고름·적용·저장이 한 줄로 도는지 검증한다."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from settings.settings_manager import SettingsManager
from settings.settings_window import SettingsWindow
from ui import theme


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def test_font_combo_exists_and_has_system_default(qapp, tmp_path):
    manager = SettingsManager(path=str(tmp_path / "config.json"))
    window = SettingsWindow(manager, lambda values: None, lambda values: None)
    combo = window.uiFontCombo
    assert combo.count() >= 1
    assert combo.itemText(0) == "시스템 기본"


def test_font_apply_persists_and_updates_theme(qapp, tmp_path):
    manager = SettingsManager(path=str(tmp_path / "config.json"))
    window = SettingsWindow(manager, lambda values: None, lambda values: None)
    window.uiFontCombo.setCurrentIndex(0)
    assert window._current_font_family() is None
    window.apply()
    assert manager.data["general"]["ui_font_family"] is None
    assert "Pretendard" not in theme.font_stack()
    available = theme._system_font_families()
    if available:
        window.uiFontCombo.setCurrentText(available[0])
        window.apply()
        assert available[0] in theme.font_stack()
