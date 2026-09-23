# -*- coding: utf-8 -*-
"""make_2x2는 서로 다른 비율의 컷도 왜곡 없이 letterbox로 배치한다."""
from PIL import Image

from compose.layout import make_2x2


def test_make_2x2_preserves_aspect_ratio_with_letterbox():
    images = [
        Image.new("RGB", (100, 100), "red"),    # 1:1 (셀은 2:1이므로 좌우 letterbox)
        Image.new("RGB", (200, 100), "green"),  # 셀과 동일 비율 → 꽉 참
        Image.new("RGB", (50, 100), "blue"),    # 세로형 (상하로 꽉, 좌우 letterbox)
        Image.new("RGB", (200, 100), "yellow"),
    ]
    canvas = make_2x2(images)

    # 셀 크기 w=200, h=100 → 캔버스 400x200
    assert canvas.size == (400, 200)

    # 1컷(100x100): 중앙 50~149 영역만 빨강, 좌우는 흰 letterbox
    assert canvas.getpixel((10, 50)) == (255, 255, 255)
    assert canvas.getpixel((100, 50)) == (255, 0, 0)
    assert canvas.getpixel((190, 50)) == (255, 255, 255)

    # 2컷(200x100): 셀을 그대로 채운다
    assert canvas.getpixel((210, 50)) == (0, 128, 0)

    # 3컷(50x100): 상하로 꽉 차고 좌우는 letterbox
    assert canvas.getpixel((10, 150)) == (255, 255, 255)
    assert canvas.getpixel((100, 150)) == (0, 0, 255)

    # 4컷: 셀 채움
    assert canvas.getpixel((210, 150)) == (255, 255, 0)


def test_make_2x2_rejects_wrong_count():
    import pytest

    with pytest.raises(ValueError):
        make_2x2([Image.new("RGB", (10, 10))])