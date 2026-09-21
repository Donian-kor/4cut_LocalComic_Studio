import time
from pathlib import Path

import requests


class ComfyUIClient:
    def __init__(self, settings):
        self.settings = dict(settings)
        self.last_prompt_id = None

    @property
    def base_url(self):
        s = self.settings
        host = str(s.get("host", "127.0.0.1")).strip()
        return f"http://{host}:{int(s.get('port', 8188))}"

    def test_connection(self, timeout=3):
        r = requests.get(self.base_url + "/system_stats", timeout=timeout)
        r.raise_for_status()
        return r.json()

    def queue_prompt(self, workflow, client_id="4cut-local"):
        r = requests.post(self.base_url + "/prompt", json={"prompt": workflow, "client_id": client_id}, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("error"):
            raise RuntimeError(f"ComfyUI workflow 오류: {data['error']}")
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI가 prompt_id를 반환하지 않았습니다: {data}")
        self.last_prompt_id = prompt_id
        return prompt_id

    def interrupt(self):
        try:
            requests.post(self.base_url + "/interrupt", timeout=3)
        except requests.RequestException:
            pass

    def wait_for_image(self, prompt_id, timeout=600, poll=0.5, cancel_check=None):
        start = time.time()
        while time.time() - start < timeout:
            if cancel_check and cancel_check():
                self.interrupt()
                raise InterruptedError("ComfyUI 이미지 생성이 취소되었습니다.")
            r = requests.get(self.base_url + f"/history/{prompt_id}", timeout=10)
            r.raise_for_status()
            history = r.json()
            if prompt_id in history:
                item = history[prompt_id]
                status = item.get("status", {})
                if status.get("status_str") == "error" or status.get("completed") is False and status.get("messages"):
                    raise RuntimeError(f"ComfyUI workflow 실행 오류: {status}")
                for node_output in item.get("outputs", {}).values():
                    # 최종 결과물(output)을 우선하고, 임시 미리보기(temp)는 나중에 본다.
                    candidates = []
                    for img in node_output.get("images", []):
                        candidates.append(img)
                        if img.get("type", "output") == "output":
                            return self.download_image(img["filename"], img.get("subfolder", ""), img.get("type", "output"))
                    if candidates:
                        img = candidates[0]
                        return self.download_image(img["filename"], img.get("subfolder", ""), img.get("type", "output"))
            time.sleep(poll)
        raise TimeoutError("ComfyUI 이미지 생성 시간이 초과되었습니다. (600초)")

    def download_image(self, filename, subfolder="", image_type="output"):
        params = {"filename": filename, "subfolder": subfolder, "type": image_type}
        r = requests.get(self.base_url + "/view", params=params, timeout=30)
        r.raise_for_status()
        return r.content

    def upload_image(self, path, timeout=60):
        """이미지를 ComfyUI input 폴더에 업로드하고 LoadImage용 이름을 반환한다."""
        p = Path(path)
        with p.open("rb") as f:
            r = requests.post(
                self.base_url + "/upload/image",
                files={"image": (p.name, f, "image/png")},
                data={"overwrite": "true"},
                timeout=timeout,
            )
        r.raise_for_status()
        data = r.json()
        name = data.get("name")
        if not name:
            raise RuntimeError(f"ComfyUI 이미지 업로드 실패: {data}")
        return name
