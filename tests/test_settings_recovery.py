# -*- coding: utf-8 -*-
"""손상된 설정 파일 격리와 원자적 저장을 검증한다."""
import json

from studio.settings.settings_manager import SettingsManager


def test_corrupt_config_is_quarantined_not_overwritten(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text("{broken json", encoding="utf-8")

    manager = SettingsManager(path=cfg)

    # 빈 설정으로 덮어쓰기 전에 원본을 격리 백업한다
    backups = list(tmp_path.glob("config.json.corrupt-*"))
    assert backups, "손상 원본이 격리 백업되어야 한다"
    assert backups[0].read_text(encoding="utf-8") == "{broken json"
    # 기본 섹션은 정상화되어 반환된다
    assert "lmstudio" in manager.data
    assert "comfyui" in manager.data

    # 저장은 임시파일 교체 방식으로 유효한 JSON만 남긴다
    manager.save()
    parsed = json.loads(cfg.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    assert not list(tmp_path.glob("*.tmp")), "임시파일이 남으면 안 된다"


def test_non_object_json_treated_as_corrupt(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text("[1, 2, 3]", encoding="utf-8")

    manager = SettingsManager(path=cfg)

    assert isinstance(manager.data, dict)
    assert list(tmp_path.glob("config.json.corrupt-*"))