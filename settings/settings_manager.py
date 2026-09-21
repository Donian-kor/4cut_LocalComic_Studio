import json
from pathlib import Path

DEFAULTS = {
    "lmstudio": {"host": "127.0.0.1", "port": 1234, "api_path": "/v1", "model": ""},
    "comfyui": {"host": "127.0.0.1", "port": 8188, "workflow": "workflows/4cut_default.json", "font_path": "", "font_size": 32},
    "general": {
        "project_path": "projects",
        "width": 768,
        "height": 768,
        "auto_save": True,
        "style_prompt": "clean anime cel shading, crisp lineart, flat colors, consistent character design",
        "bubble_font_size": 28,
    },
}


class SettingsManager:
    def __init__(self, path=None):
        base = Path(__file__).resolve().parent.parent
        self.base_dir = base
        self.path = Path(path) if path else base / "config" / "config.json"
        if not self.path.is_absolute():
            self.path = base / self.path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()
        self._normalize()

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _normalize(self):
        for name, values in DEFAULTS.items():
            section = self.data.setdefault(name, {})
            for key, value in values.items():
                section.setdefault(key, value)

    def save(self):
        self._normalize()
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def section(self, name):
        return self.data.setdefault(name, {})

    def resolve_path(self, value):
        path = Path(value)
        return path if path.is_absolute() else self.base_dir / path
