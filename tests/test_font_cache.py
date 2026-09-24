# -*- coding: utf-8 -*-
"""폰트 캐시가 (경로, 크기) 키로 동작하는지 검증한다."""
import os
from pathlib import Path

from studio.services.bubble import _FONT_CACHE, find_font


def test_find_font_caches_by_path_and_size():
    a = find_font(32)
    b = find_font(32)
    assert a is b  # 같은 (경로, 크기)는 캐시 재사용

    c = find_font(33)
    assert c is not a  # 크기가 다르면 별도 캐시

    assert ("", 32) in _FONT_CACHE
    assert ("", 33) in _FONT_CACHE


def test_find_font_with_explicit_path_uses_separate_cache_key():
    font = find_font(24, "C:/nonexistent-dir/none.ttf")
    assert font is not None  # 지정 경로가 없으면 시스템 폰트로 대체
    assert ("C:/nonexistent-dir/none.ttf", 24) in _FONT_CACHE


def test_configured_font_path_used_when_available():
    windir = Path(os.environ.get("WINDIR", "C:/Windows"))
    path = windir / "Fonts" / "malgun.ttf"
    if not path.exists():
        import pytest

        pytest.skip("malgun.ttf 없음(비 Windows 환경)")
    font = find_font(28, str(path))
    assert getattr(font, "size", 28) == 28
    # 캐시 키는 백슬래시를 정규화해 저장한다
    assert (str(path).replace("\\", "/"), 28) in _FONT_CACHE