# -*- coding: utf-8 -*-
"""Sidebar 제목 정규화가 상태 꼬리표만 제거하고 본문 문자는 보존하는지 검증한다.

`_rename_changed`가 과거처럼 rstrip("⟳!·")로 제목 끝의 정상 문자(!, · 등)까지
잘라내지 않는지 확인한다.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from studio.ui.sidebar import Sidebar


def test_rename_keeps_trailing_punctuation_and_strips_status_suffix():
    app = QApplication.instance() or QApplication([])
    sidebar = Sidebar()
    sidebar.list.addItem("dummy")
    item = sidebar.list.item(0)
    item.setData(Qt.ItemDataRole.UserRole, "s1")

    captured = []
    sidebar.sessionRenamed.connect(lambda sid, title: captured.append((sid, title)))

    cases = [
        ("재밌는 이야기!", "재밌는 이야기!"),  # 본문 끝의 !는 보존
        ("낮·밤", "낮·밤"),                     # 본문 끝의 ·는 보존
        ("내 만화  !", "내 만화"),               # 상태 꼬리표만 제거
        ("대화  ⟳", "대화"),
        ("실패한 시도  ·", "실패한 시도"),
    ]
    for display, expected in cases:
        sidebar.list.blockSignals(True)
        item.setText(display)
        sidebar.list.blockSignals(False)
        sidebar._rename_changed(item)
        assert captured[-1] == ("s1", expected), display

    assert len(captured) == len(cases)
    assert app is not None
