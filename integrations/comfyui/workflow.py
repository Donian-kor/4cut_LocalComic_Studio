import json
from pathlib import Path

class WorkflowAdapter:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def prepare(self, prompt, seed, width, height):
        wf = self.load()
        # Starter workflow node IDs. Adjust these for a custom ComfyUI API workflow.
        if "1" in wf and "inputs" in wf["1"]:
            wf["1"]["inputs"]["text"] = prompt
        if "2" in wf and "inputs" in wf["2"]:
            wf["2"]["inputs"]["seed"] = int(seed)
        if "6" in wf and "inputs" in wf["6"]:
            wf["6"]["inputs"]["width"] = int(width)
            wf["6"]["inputs"]["height"] = int(height)
        return wf
