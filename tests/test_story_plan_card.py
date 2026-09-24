# -*- coding: utf-8 -*-
"""스토리 계획 카드가 원본 프롬프트 없이 구조화된 요약을 표시하는지 검증한다."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from studio.ui.chat_widgets import StoryPlanCard


def test_story_plan_card_displays_readable_summary_without_image_prompt():
    app = QApplication.instance() or QApplication([])
    card = StoryPlanCard({
        "title": "장미와 와인",
        "mood": "로맨틱",
        "art_style": "웹툰",
        "character": {"name": "민준", "appearance": "네이비 재킷", "personality": "다정함"},
        "panels": [{"scene": "바에서 장미를 건넨다", "dialogue": "받아 주세요.", "speaker": "민준"}],
    })

    labels = "\n".join(label.text() for label in card.findChildren(QLabel))
    assert "장미와 와인" in labels
    assert "민준" in labels
    assert "바에서 장미를 건넨다" in labels
    assert "민준: 받아 주세요." in labels
    assert "image_prompt" not in labels
    assert app is not None
