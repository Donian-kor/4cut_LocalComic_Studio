from pathlib import Path

from core.models.comic import Comic, Character, Panel
from core.services.comic_service import ComicService


class FakeImageService:
    def __init__(self):
        self.calls = []

    def generate_panel(self, panel, output_dir, cancel_check=None, style_prompt=""):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"panel_{panel.index}.png"
        path.write_bytes(b"panel")
        panel.image_path = str(path)
        self.calls.append((panel.index, panel.seed, panel.revision_prompt, style_prompt))
        return str(path)

    def apply_dialogue(self, panel, **kwargs):
        path = Path(panel.image_path)
        dialogued = path.with_name(path.stem + "_dialogue.png")
        dialogued.write_bytes(b"dialogue")
        panel.image_path = str(dialogued)
        panel.dialogue_composited = True
        return str(dialogued)


class FakeComposeService:
    def __init__(self):
        self.calls = 0

    def compose(self, comic, output_path):
        self.calls += 1
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_bytes(b"final")
        comic.output_path = str(output_path)
        return str(output_path)


class FakeWorkflow:
    stage2_path = None


def make_comic():
    comic = Comic(
        idea="회사 개그",
        title="월요병",
        character=Character(name="민수", appearance="검은 머리"),
        master_seed=12345,
        character_prompt="민수: 검은 머리",
        style_prompt="webtoon style",
        generation_config={"id": "model-a", "steps": 28, "cfg": 4.0, "sampler": "euler_ancestral", "scheduler": "beta"},
    )
    for i in range(1, 5):
        comic.panels.append(Panel(i, scene=f"장면 {i}", image_prompt=f"prompt {i}", dialogue=f"대사 {i}", seed=12345))
    return comic


def test_comic_roundtrip_keeps_panel_regeneration_data():
    comic = make_comic()
    comic.panels[1].revision_prompt = "웃는 표정을 더 크게"
    comic.panels[1].revision_count = 2
    restored = Comic.from_dict(comic.to_dict())

    assert restored.master_seed == 12345
    assert restored.character_prompt == comic.character_prompt
    assert restored.style_prompt == comic.style_prompt
    assert restored.panels[1].revision_prompt == "웃는 표정을 더 크게"
    assert restored.panels[1].revision_count == 2


def test_regenerate_panel_changes_only_target_seed_and_recomposes(tmp_path):
    service = ComicService.__new__(ComicService)
    service.image = FakeImageService()
    service.compose_service = FakeComposeService()
    service.workflow = FakeWorkflow()
    service.font_name = "malgun.ttf"
    service.style_prompt = "fallback style"
    service._run_folder = tmp_path / "run"

    comic = make_comic()
    original_seeds = [p.seed for p in comic.panels]
    path = service.regenerate_panel(comic, 2, revision="웃는 표정을 더 크게")
    final = service.compose(comic)

    assert Path(path).exists()
    assert Path(final).exists()
    assert comic.panels[1].revision_prompt == "웃는 표정을 더 크게"
    assert comic.panels[1].seed != original_seeds[1]
    assert [p.seed for p in comic.panels[:1] + comic.panels[2:]] == [12345, 12345, 12345]
    assert service.compose_service.calls == 1
    assert service.image.calls[0][0] == 2
