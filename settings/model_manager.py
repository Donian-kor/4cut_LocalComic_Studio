import re
from core.models.image_model import ImageModelProfile


DEFAULT_IMAGE_MODELS = [
    ImageModelProfile(
        id="z_anime_base_aio_fp8",
        name="Z-Anime Base AIO FP8",
        model_file="z-anime-base-aio-fp8.safetensors",
        workflow="workflows/z_anime_base_aio_fp8.json",
        width=512,
        height=512,
        steps=28,
        cfg=4.0,
        sampler="euler_ancestral",
        scheduler="beta",
        negative_prompt="low quality, blurry, deformed, bad anatomy, extra fingers, extra limbs, distorted face",
    )
]


class ImageModelManager:
    def __init__(self, settings_manager):
        self.settings = settings_manager
        self._ensure_defaults()

    def _ensure_defaults(self):
        raw = self.settings.data.get("image_models")
        if not isinstance(raw, list) or not raw:
            self.settings.data["image_models"] = [m.to_dict() for m in DEFAULT_IMAGE_MODELS]
        else:
            # Keep user profiles, but normalize malformed entries.
            self.settings.data["image_models"] = [
                ImageModelProfile.from_dict(x).to_dict() for x in raw if isinstance(x, dict)
            ] or [m.to_dict() for m in DEFAULT_IMAGE_MODELS]
        selected = self.settings.data.get("image_model", "")
        ids = {m["id"] for m in self.settings.data["image_models"]}
        if selected not in ids:
            self.settings.data["image_model"] = self.settings.data["image_models"][0]["id"]

    def profiles(self):
        return [ImageModelProfile.from_dict(x) for x in self.settings.data["image_models"]]

    def get(self, model_id=None):
        model_id = model_id or self.settings.data.get("image_model")
        for profile in self.profiles():
            if profile.id == model_id:
                return profile
        profiles = self.profiles()
        return profiles[0] if profiles else None

    def selected_id(self):
        return str(self.settings.data.get("image_model", ""))

    def select(self, model_id):
        if any(p.id == model_id for p in self.profiles()):
            self.settings.data["image_model"] = model_id

    def upsert(self, profile):
        if not profile.id.strip():
            profile.id = self._make_id(profile.name)
        profiles = self.profiles()
        replaced = False
        for i, current in enumerate(profiles):
            if current.id == profile.id:
                profiles[i] = profile
                replaced = True
                break
        if not replaced:
            profiles.append(profile)
        self.settings.data["image_models"] = [p.to_dict() for p in profiles]
        self.select(profile.id)
        return profile

    def remove(self, model_id):
        profiles = [p for p in self.profiles() if p.id != model_id]
        if not profiles:
            return False
        self.settings.data["image_models"] = [p.to_dict() for p in profiles]
        if self.selected_id() == model_id:
            self.settings.data["image_model"] = profiles[0].id
        return True

    def save(self):
        self.settings.save()

    @staticmethod
    def _make_id(name):
        value = re.sub(r"[^a-zA-Z0-9가-힣]+", "_", name.strip()).strip("_").lower()
        return value or "custom_model"
