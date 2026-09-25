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

from PySide6.QtWidgets import QApplication, QFrame, QLayout, QLabel, QSplitter  # noqa: E402

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


def test_header_removed_and_status_label_left_of_send_button():
    app = _app()
    window = _make_window()
    try:
        window.show()
        app.processEvents()

        # 창 안 헤더(제목/로고)는 제거, 타이틀바는 짧은 이름만 남는다(A안).
        assert window.findChild(QFrame, "headerFrame") is None
        assert window.findChild(QLabel, "logoLabel") is None
        assert window.windowTitle() == "4cut Studio"

        # 상태 라벨은 composer의 전송버튼 왼쪽에 있어야 한다.
        assert window.status_label is not None
        assert window.status_label.objectName() == "saveStatusLabel"
        options = window.composer.form.findChild(QLayout, "optionsLayout")
        assert options is not None
        assert 0 <= options.indexOf(window.status_label) < options.indexOf(window.composer.send)
        assert window.status_label.isVisibleTo(window)
    finally:
        window.close()
        app.processEvents()


def test_empty_and_chat_hosts_toggle_container_visibility():
    app = _app()
    window = _make_window()
    try:
        window.show()
        app.processEvents()

        # 초기: 빈 화면만 보이고 채팅 Host는 접혀 있어야 한다(반반 분할 회귀 방지).
        assert window.empty.isVisibleTo(window)
        assert window.empty_host.isVisibleTo(window)
        assert window.chat_host.isHidden()

        # 채팅 표시 시 emptyHost 컨테이너 전체가 숨고 chatHost가 공간을 가져야 한다.
        window.chat_view.set_empty_visible(False)
        app.processEvents()
        assert window.chat.isVisibleTo(window)
        assert window.chat_host.isVisibleTo(window)
        assert window.empty_host.isHidden()

        # 다시 빈 화면으로 돌아가면 그 반대.
        window.chat_view.set_empty_visible(True)
        app.processEvents()
        assert window.empty.isVisibleTo(window)
        assert window.empty_host.isVisibleTo(window)
        assert window.chat_host.isHidden()
    finally:
        window.close()
        app.processEvents()
