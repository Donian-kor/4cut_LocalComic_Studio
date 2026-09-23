import json
import shutil
import time
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
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("설정 JSON 최상위가 객체가 아닙니다.")
            return data
        except Exception as exc:
            # 손상된 설정 원본을 격리해 복구하고, 빈 설정으로 즉시 덮어쓰지 않는다.
            try:
                backup = self.path.with_name(f"{self.path.name}.corrupt-{int(time.time())}")
                shutil.copy2(self.path, backup)
                print(f"[SettingsManager] 설정 파일 손상({exc}) → 원본 격리: {backup}")
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
        tmp = self.path.with_name(f"{self.path.name}.tmp")
        tmp.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(self.path)

    def section(self, name):
        return self.data.setdefault(name, {})

    def resolve_path(self, value):
        path = Path(value)
        return path if path.is_absolute() else self.base_dir / path
