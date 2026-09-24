from PySide6.QtCore import QThread, Signal


class ServerStatusWorker(QThread):
    checked = Signal(bool, bool, str)

    def __init__(self, lm_factory, comfy_factory, settings_manager, parent=None):
        super().__init__(parent)
        self.lm_factory = lm_factory
        self.comfy_factory = comfy_factory
        self.settings_manager = settings_manager

    def run(self):
        lm_ok = False
        comfy_ok = False
        errors = []
        try:
            lm = self.lm_factory(dict(self.settings_manager.section("lmstudio")))
            lm.test_connection(timeout=2)
            lm_ok = True
        except Exception as e:
            errors.append(f"LM Studio: {e}")
        try:
            comfy = self.comfy_factory(dict(self.settings_manager.section("comfyui")))
            comfy.test_connection(timeout=2)
            comfy_ok = True
        except Exception as e:
            errors.append(f"ComfyUI: {e}")
        self.checked.emit(lm_ok, comfy_ok, " / ".join(errors))
