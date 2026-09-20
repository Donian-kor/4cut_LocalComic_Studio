import time
import requests

class ComfyUIClient:
    def __init__(self, settings):
        self.settings = settings
        self.last_prompt_id = None

    @property
    def base_url(self):
        s = self.settings
        return f"http://{s.get('host','127.0.0.1')}:{int(s.get('port',8188))}"

    def test_connection(self, timeout=3):
        r = requests.get(self.base_url + "/system_stats", timeout=timeout)
        r.raise_for_status()
        return r.json()

    def queue_prompt(self, workflow, client_id="4cut-local"):
        r = requests.post(self.base_url + "/prompt", json={"prompt": workflow, "client_id": client_id}, timeout=10)
        r.raise_for_status()
        data = r.json()
        self.last_prompt_id = data.get("prompt_id")
        return self.last_prompt_id

    def interrupt(self):
        try:
            requests.post(self.base_url + "/interrupt", timeout=3)
        except Exception:
            pass

    def wait_for_image(self, prompt_id, timeout=600, poll=1.0):
        start = time.time()
        while time.time() - start < timeout:
            r = requests.get(self.base_url + f"/history/{prompt_id}", timeout=10)
            r.raise_for_status()
            history = r.json()
            if prompt_id in history:
                item = history[prompt_id]
                outputs = item.get("outputs", {})
                for node_output in outputs.values():
                    for img in node_output.get("images", []):
                        return self.download_image(img["filename"], img.get("subfolder",""), img.get("type","output"))
                if item.get("status", {}).get("status_str") == "error":
                    raise RuntimeError("ComfyUI workflow error")
            time.sleep(poll)
        raise TimeoutError("ComfyUI generation timed out")

    def download_image(self, filename, subfolder="", image_type="output"):
        params = {"filename": filename, "subfolder": subfolder, "type": image_type}
        r = requests.get(self.base_url + "/view", params=params, timeout=30)
        r.raise_for_status()
        return r.content
