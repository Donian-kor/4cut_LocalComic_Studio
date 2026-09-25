# -*- coding: utf-8 -*-
"""설정창 '이미지 모델' 탭 레이아웃 회귀 방지 테스트.

- 워크플로우 도우미(실험적 버튼+상태 라벨)는 Designer(.ui)에 정의되어 있어야 한다.
- 너비/높이는 한 줄, Negative Prompt는 최대 3줄로 고정한다.
"""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFormLayout, QLabel, QPlainTextEdit, QPushButton, QSpinBox  # noqa: E402

from studio.settings.settings_manager import SettingsManager  # noqa: E402
from studio.settings.settings_window import SettingsWindow  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LABEL_ROLE = QFormLayout.ItemRole.LabelRole
FIELD_ROLE = QFormLayout.ItemRole.FieldRole


def _window(tmp_path):
    QApplication.instance() or QApplication([])
    manager = SettingsManager(path=str(tmp_path / "resources" / "config.json"))
    return SettingsWindow(manager, lambda values: None, lambda values: None)


def _form(window):
    form = window.form.findChild(QFormLayout, "imageModelForm")
    assert form is not None
    return form


def _row_of(form, widget):
    """QFormLayout의 (중첩 레이아웃 포함) 행 번호를 찾는다."""
    for row in range(form.rowCount()):
        for role in (LABEL_ROLE, FIELD_ROLE):
            item = form.itemAt(row, role)
            if item is None:
                continue
            if item.widget() is widget:
                return row
            layout = item.layout()
            if layout is not None and layout.indexOf(widget) >= 0:
                return row
    raise AssertionError(f"폼에서 위젯을 찾지 못했습니다: {widget.objectName()}")


def test_helper_widgets_are_defined_in_designer_ui():
    ui_text = (ROOT / "studio" / "ui" / "settings_window.ui").read_text(encoding="utf-8")
    for name in ("aiWorkflowButton", "workflowStatusLabel"):
        assert f'name="{name}"' in ui_text, name
    for name in ("stage2WorkflowEdit", "stage2BrowseButton", "stage2WorkflowLabel"):
        assert f'name="{name}"' not in ui_text, name

    # 이미지 모델 폼 위젯을 파이썬에서 새로 만들거나 뒤에 덧붙이지 않는다(Designer 정의만 사용).
    source = (ROOT / "studio" / "settings" / "settings_window.py").read_text(encoding="utf-8")
    for token in ("QPushButton(", "QLineEdit(", "QHBoxLayout(", "QFormLayout(", "imageModelForm"):
        assert token not in source, token


def test_window_exposes_helper_widgets_from_ui(tmp_path):
    window = _window(tmp_path)
    try:
        assert isinstance(window.aiWorkflowButton, QPushButton)
        assert isinstance(window.workflowStatusLabel, QLabel)
        assert window.workflowStatusLabel.wordWrap() is True
        assert not hasattr(window, "stage2WorkflowEdit")
        assert not hasattr(window, "stage2BrowseButton")
    finally:
        window.form.close()


def test_helper_row_is_right_below_workflow_row(tmp_path):
    window = _window(tmp_path)
    try:
        form = _form(window)
        workflow_row = _row_of(form, window.form.imageModelWorkflowEdit)
        helper_row = _row_of(form, window.aiWorkflowButton)
        assert helper_row == workflow_row + 1
        # 버튼과 상태 라벨은 같은 칸(레이아웃)에 세로로 쌓인다.
        assert _row_of(form, window.workflowStatusLabel) == helper_row
        assert form.itemAt(helper_row, LABEL_ROLE).widget().objectName() == "workflowHelperLabel"
    finally:
        window.form.close()


def test_width_and_height_share_one_row(tmp_path):
    window = _window(tmp_path)
    try:
        form = _form(window)
        width_spin = window.form.imageModelWidthSpin
        height_spin = window.form.imageModelHeightSpin
        assert isinstance(width_spin, QSpinBox) and isinstance(height_spin, QSpinBox)
        assert _row_of(form, width_spin) == _row_of(form, height_spin)
        layout = form.itemAt(_row_of(form, width_spin), FIELD_ROLE).layout()
        assert layout is not None
        assert layout.indexOf(width_spin) >= 0 and layout.indexOf(height_spin) >= 0
        assert width_spin.maximumWidth() <= 200
    finally:
        window.form.close()


def test_negative_prompt_limited_to_three_lines(tmp_path):
    window = _window(tmp_path)
    try:
        edit = window.form.imageModelNegativeEdit
        assert isinstance(edit, QPlainTextEdit)
        assert 0 < edit.maximumHeight() <= 72
        assert edit.minimumHeight() >= 60
    finally:
        window.form.close()
