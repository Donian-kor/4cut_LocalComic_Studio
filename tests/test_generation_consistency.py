# -*- coding: utf-8 -*-
"""4컷 생성 시 일관성 컨텍스트가 한 만화 안에서 고정되는지 검증한다."""

from types import SimpleNamespace

from studio.services.story_service import StoryService
from studio.integrations.workflow import WorkflowAdapter


class FakeLLM:
    def chat_json(self, system, user, cancel_check=None):
        return {
            "title": "회사 월요일",
            "style": "ignored-by-test",
            "character": {
                "name": "민수",
                "appearance": "검은 단발머리, 둥근 안경, 파란 셔츠, 작은 체격",
                "personality": "낙천적",
            },
            "panels": [
                {"scene": "사무실 책상에 앉아 있음", "dialogue": "월요일이다.", "speaker": "민수", "image_prompt": "a character at a desk"},
                {"scene": "복도를 걷고 있음", "dialogue": "벌써 점심인가?", "speaker": "민수", "image_prompt": "the character walking in an office hallway"},
                {"scene": "동료와 대화함", "dialogue": "퇴근하고 싶다.", "speaker": "민수", "image_prompt": "the character talking with a coworker"},
                {"scene": "놀란 표정으로 뒤를 돌아봄", "dialogue": "회의라고요?", "speaker": "민수", "image_prompt": "the character looking back with surprise"},
            ],
        }


def test_master_seed_and_shared_prompts_are_fixed_for_all_panels():
    service = StoryService(FakeLLM())
    requested_style = "modern Korean webtoon illustration style, soft pastel palette"
    comic = service.create_comic("회사원의 월요일", requested_style)

    assert comic.master_seed != 0
    assert comic.style_prompt == requested_style
    assert comic.character_prompt == "민수: 검은 단발머리, 둥근 안경, 파란 셔츠, 작은 체격"
    assert len({panel.seed for panel in comic.panels}) == 1

    for panel in comic.panels:
        assert comic.character_prompt in panel.image_prompt
        assert comic.style_prompt in panel.image_prompt


def test_workflow_applies_the_same_seed_and_profile_to_each_panel(tmp_path):
    workflow_file = tmp_path / "workflow.json"
    workflow_file.write_text(
        """{
  \"1\": {\"class_type\": \"CLIPTextEncode\", \"inputs\": {\"text\": \"\"}},
  \"2\": {\"class_type\": \"CLIPTextEncode\", \"inputs\": {\"text\": \"\"}},
  \"3\": {\"class_type\": \"KSampler\", \"inputs\": {\"seed\": 1, \"steps\": 1, \"cfg\": 1, \"sampler_name\": \"euler\", \"scheduler\": \"normal\"}},
  \"4\": {\"class_type\": \"EmptyLatentImage\", \"inputs\": {\"width\": 512, \"height\": 512, \"batch_size\": 1}},
  \"5\": {\"class_type\": \"CheckpointLoaderSimple\", \"inputs\": {\"ckpt_name\": \"old.safetensors\"}}
}""",
        encoding="utf-8",
    )
    profile = SimpleNamespace(
        width=768,
        height=768,
        steps=28,
        cfg=4.0,
        sampler="euler_ancestral",
        scheduler="beta",
        model_file="new.safetensors",
        negative_prompt="low quality",
    )
    adapter = WorkflowAdapter(workflow_file, profile=profile)

    seed = 123456789
    wf1 = adapter.prepare("panel one", seed, style_prompt="webtoon style")
    wf2 = adapter.prepare("panel two", seed, style_prompt="webtoon style")

    for wf in (wf1, wf2):
        sampler = wf["3"]["inputs"]
        assert sampler["seed"] == seed
        assert sampler["steps"] == 28
        assert sampler["cfg"] == 4.0
        assert sampler["sampler_name"] == "euler_ancestral"
        assert sampler["scheduler"] == "beta"
        assert wf["5"]["inputs"]["ckpt_name"] == "new.safetensors"

    assert wf1["1"]["inputs"]["text"] != wf2["1"]["inputs"]["text"]
    assert "webtoon style" in wf1["1"]["inputs"]["text"]
    assert "webtoon style" in wf2["1"]["inputs"]["text"]
