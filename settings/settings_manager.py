import json
from pathlib import Path

class SettingsManager:
    def __init__(self, path="config/config.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self):
        if not self.path.exists():
            return {
                "lmstudio": {"host": "127.0.0.1", "port": 1234, "api_path": "/v1", "model": ""},
                "comfyui": {"host": "127.0.0.1", "port": 8188, "workflow": "workflows/4cut_default.json"},
                "general": {"project_path": "projects", "width": 768, "height": 768, "auto_save": True},
            }
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def section(self, name):
        return self.data.setdefault(name, {})
