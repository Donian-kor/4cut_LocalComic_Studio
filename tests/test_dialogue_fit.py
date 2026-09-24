from types import SimpleNamespace

from studio.services.image_service import ImageService


def test_dialogue_auto_fit_does_not_exceed_configured_font_size():
    service = ImageService(None, SimpleNamespace(font_path=""), width=512, height=512)
    _, fitted_size = service._fit_dialogue_text("짧은 대사", target_width=450, target_height=180)
    assert fitted_size <= 110


def test_fallback_font_shrinks_long_dialogue_to_fit():
    from studio.services.compose_service import ComposeService
    service = ComposeService()
    font = service._fit_fallback_font("긴 대사 " * 30, 180, 70)
    assert font.size < 110
