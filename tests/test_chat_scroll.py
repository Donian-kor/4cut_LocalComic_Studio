# -*- coding: utf-8 -*-
"""ChatScrollArea의 하단 고정/위치 유지 동작을 검증한다.

컷 완료 시 생성 카드 제거 → 결과 카드 추가 → 이미지 재렌더로 콘텐츠
높이가 연속으로 변할 때 스크롤이 "내려갔다가 올라가는" 왕복 점프 없이
하단을 일관되게 따라가는지 확인한다.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QFrame

from studio.ui.chat_widgets import ChatScrollArea


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def _drain(app, rounds=10):
    """레이아웃 확정과 singleShot(0) 타이머가 소진될 때까지 이벤트를 돌린다."""
    for _ in range(rounds):
        app.processEvents()


def _make_area(app):
    area = ChatScrollArea()
    area.resize(400, 300)
    area.show()
    _drain(app)
    return area


def _block(height):
    widget = QFrame()
    widget.setFixedHeight(height)
    return widget


def _fill(app, area, count=6, height=200):
    blocks = []
    for _ in range(count):
        block = _block(height)
        area.append(block)
        blocks.append(block)
        _drain(app)
    return blocks


def test_appends_keep_view_at_bottom(qapp):
    area = _make_area(qapp)
    _fill(qapp, area)

    bar = area.verticalScrollBar()
    assert bar.maximum() > 0
    assert bar.value() == bar.maximum()


def test_remove_append_and_growth_keep_bottom(qapp):
    """컷 완료 시나리오: 생성 카드 제거 → 결과 카드 추가 → 이미지 재렌더 성장."""
    area = _make_area(qapp)
    blocks = _fill(qapp, area)
    bar = area.verticalScrollBar()
    assert bar.value() == bar.maximum()

    for cycle in range(3):
        area.remove_widget(blocks[-1])
        blocks.pop()
        _drain(qapp)

        result = _block(150)
        area.append(result)
        blocks.append(result)
        _drain(qapp)
        assert bar.value() == bar.maximum(), f"cycle {cycle}: 카드 교체 후 하단 유지"

        # 이미지 레이블이 레이아웃 이후 실제 크기로 재렌더되어 높이가 자라는 상황
        result.setFixedHeight(500)
        _drain(qapp)
        assert bar.value() == bar.maximum(), f"cycle {cycle}: 높이 성장 후 하단 유지"


def test_scrolled_up_position_is_preserved(qapp):
    """하단을 벗어난 사용자의 위치에서 새 메시지가 추가되어도 움직이지 않는다."""
    area = _make_area(qapp)
    _fill(qapp, area)
    bar = area.verticalScrollBar()

    mid = bar.maximum() // 2
    bar.setValue(mid)  # 사용자 직접 스크롤로 취급 → 따라가기 해제
    _drain(qapp)
    assert not area._stick_to_bottom

    area.append(_block(200))
    _drain(qapp)
    assert bar.value() == mid

    # 높이가 줄어도(상단/일부 위젯 제거 시 클램프가 없으면) 위치 유지
    area.append(_block(300))
    _drain(qapp)
    assert bar.value() == mid


def test_following_resumes_when_user_returns_to_bottom(qapp):
    area = _make_area(qapp)
    _fill(qapp, area)
    bar = area.verticalScrollBar()

    bar.setValue(bar.maximum() // 2)
    _drain(qapp)
    assert not area._stick_to_bottom

    bar.setValue(bar.maximum())  # 사용자가 하단으로 복귀
    _drain(qapp)
    assert area._stick_to_bottom

    area.append(_block(200))
    _drain(qapp)
    assert bar.value() == bar.maximum()