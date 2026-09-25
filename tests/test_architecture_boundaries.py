from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imports(path):
    tree = _tree(path)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            out.append(node.module or "")
    return out


def test_main_controller_does_not_import_ui_modules():
    imports = _imports(ROOT / "studio" / "main_controller.py")
    assert all(not name.startswith("studio.ui") for name in imports)


def test_chat_view_manager_does_not_mutate_session_model():
    source = (ROOT / "studio" / "ui" / "chat_view_manager.py").read_text(encoding="utf-8")
    forbidden = ("session.status =", "session.error_message =", "session.messages =", "session.panel_paths =",
                 "session.result_path =", "session.master_seed =", "session.character_prompt =",
                 "session.style_prompt =", "session.generation_config =", "session.comic_data =",
                 "session.add_message(", "session.touch()")
    assert not any(token in source for token in forbidden)


def test_main_window_does_not_build_layout_in_python():
    source = (ROOT / "studio" / "ui" / "main_window.py").read_text(encoding="utf-8")
    for token in ("QSplitter(", "QVBoxLayout(", "QHBoxLayout(", "QPushButton(", "QLabel("):
        assert token not in source


def test_main_window_does_not_mutate_sessions():
    source = (ROOT / "studio" / "ui" / "main_window.py").read_text(encoding="utf-8")
    for token in ("session_manager.add(", "session_manager.update(", "session_manager.remove(", "session.touch()", "session.messages ="):
        assert token not in source


def test_main_window_has_designer_ui():
    ui = ROOT / "studio" / "ui" / "main_window.ui"
    assert ui.exists()
    text = ui.read_text(encoding="utf-8")
    for name in ("mainSplitter", "sidebarHost", "emptyHost", "chatHost", "composerHost"):
        assert f'name="{name}"' in text
    # 헤더(제목/로고/상태라벨)는 제거됐다 — 타이틀바 중복 제목 정리.
    assert 'name="headerFrame"' not in text
    assert 'name="logoLabel"' not in text
    assert 'name="saveStatusLabel"' not in text


def test_composer_has_status_label_left_of_send_button():
    ui = ROOT / "studio" / "ui" / "composer.ui"
    assert ui.exists()
    text = ui.read_text(encoding="utf-8")
    # 상태라벨은 헤더 대신 전송버튼 왼쪽에 배치되어야 한다.
    assert 'name="saveStatusLabel"' in text
    assert text.index('name="saveStatusLabel"') < text.index('name="sendButton"')


def test_shared_presets_have_expected_keys():
    from studio.core.presets import ART_STYLE_PRESETS, STYLE_PRESETS
    assert "자동" in STYLE_PRESETS
    assert "캐주얼 만화" in ART_STYLE_PRESETS
