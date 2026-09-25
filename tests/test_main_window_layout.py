# -*- coding: utf-8 -*-
"""MainWindow 위젯 배치 회귀 방지 smoke 테스트.

- 사이드바/컴포지터가 Host 레이아웃에 실제로 배치되는지
- mainSplitter 초기 폭이 0px로 접히지 않는지
- 빈 화면/채팅 뷰가 Host 레이아웃에 배치되는지
"""

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QSplitter  # noqa: E402

from studio.ui.main_window import MainWindow  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _app():
    return QApplication.instance() or QApplication([])


def _make_window():
    settings = SimpleNamespace(data={"general": {}}, base_dir=ROOT)
    return MainWindow(settings, lambda: None, lambda: None)


def test_main_window_hosts_children_in_layouts():
    app = _app()
    window = _make_window()
    try:
        window.show()
        app.processEvents()

        # 사이드바/컴포지터가 Host 레이아웃에 배치되어야 화면에 보인다.
        assert window.sidebar_host.layout().indexOf(window.sidebar) >= 0
        assert window.composer_host.layout().indexOf(window.composer) >= 0
        assert window.sidebar.parentWidget() is window.sidebar_host
        assert window.composer.parentWidget() is window.composer_host

        # 채팅/빈 상태 뷰도 Host 레이아웃에 배치되어야 한다.
        assert window.chat_host.layout().indexOf(window.chat) >= 0
        assert window.empty_host.layout().indexOf(window.empty) >= 0

        # 위젯이 실제로 보이는 영역에 있는지(0px 폭/높이 회귀 방지).
        assert window.sidebar.width() > 0
        assert window.composer.height() > 0
        assert window.sidebar.isVisibleTo(window)
        assert window.composer.isVisibleTo(window)

        # 스플리터 초기 폭이 sidebar 쪽으로 0px 접히지 않는다.
        splitter = window.findChild(QSplitter, "mainSplitter")
        assert splitter is not None
        sizes = splitter.sizes()
        assert sizes[0] > 0
        assert window.sidebar.minimumWidth() >= 200
    finally:
        window.close()
        app.processEvents()
