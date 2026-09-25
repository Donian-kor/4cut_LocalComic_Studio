import json
import logging
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULTS = {
    "lmstudio": {"host": "127.0.0.1", "port": 1234, "api_path": "/v1", "model": ""},
    "comfyui": {"host": "127.0.0.1", "port": 8188, "workflow": "resources/4cut_default.json", "font_path": ""},
    "general": {
        "project_path": "projects",
        "width": 512,
        "height": 512,
        "auto_save": True,
        "style_prompt": "clean anime cel shading, crisp lineart, flat colors, consistent character design",
        "art_style_prompt": "",
        "ui_font_family": None,
    },
}


class SettingsManager:
    def __init__(self, path=None):
        # settings/settings_manager.py → studio/ → 프로젝트 루트 (3단계 상위)
        base = Path(__file__).resolve().parents[2]
        self.base_dir = base
        self.path = Path(path) if path else base / "resources" / "config.json"
        if not self.path.is_absolute():
            self.path = base / self.path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy_config()
        self.data = self._load()
        self._normalize()

    def _migrate_legacy_config(self):
        """기존 구조의 config/config.json을 resources/config.json으로 1회성 이관한다.

        - 이관 시 workflow 경로의 "workflows/" 접두사를 "resources/"로 바꾼다.
        - 이관이 끝나면 원본은 config.json.migrated로 남겨 되돌릴 수 있게 한다.
        """
        legacy = self.base_dir / "config" / "config.json"
        if self.path.exists() or not legacy.is_file():
            return
        try:
            raw = legacy.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("설정 JSON 최상위가 객체가 아닙니다.")
            for section in data.values():
                if isinstance(section, dict):
                    for key, value in list(section.items()):
                        if isinstance(value, str) and value.startswith("workflows/"):
                            section[key] = "resources/" + value[len("workflows/"):]
                elif isinstance(section, list):
                    for entry in section:
                        if isinstance(entry, dict):
                            for key, value in list(entry.items()):
                                if isinstance(value, str) and value.startswith("workflows/"):
                                    entry[key] = "resources/" + value[len("workflows/"):]
            self.path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            legacy.replace(legacy.with_name("config.json.migrated"))
            logger.info(
                "기존 설정(config/config.json)을 resources/config.json으로 이관했습니다."
            )
        except Exception as exc:
            logger.warning("기존 설정 이관 실패(원본 유지): %s", exc)

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("설정 JSON 최상위가 객체가 아닙니다.")
            return data
        except Exception as exc:
            # 손상된 설정 원본을 격리해 복구하고, 빈 설정으로 즉시 덮어쓰지 않는다.
            try:
                backup = self.path.with_name(f"{self.path.name}.corrupt-{int(time.time())}")
                shutil.copy2(self.path, backup)
                logger.warning("설정 파일 손상(%s) → 원본 격리: %s", exc, backup)
            except OSError:
                pass
            return {}

    def _normalize(self):
        for name, values in DEFAULTS.items():
            section = self.data.setdefault(name, {})
            for key, value in values.items():
                section.setdefault(key, value)

    def save(self):
        self._normalize()
        # 임시파일에 먼저 쓰고 원자적으로 교체해 중간 종료 시 파일 손상을 막는다.
        tmp = self.path.with_name(f"{self.path.name}.{uuid.uuid4().hex}.tmp")
        tmp.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(self.path)

    def section(self, name: str) -> dict[str, Any]:
        return self.data.setdefault(name, {})

    def resolve_path(self, value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else self.base_dir / path
