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
        pending_polls = 0
        while time.time() - start < timeout:
            if cancel_check and cancel_check():
                # interrupt는 worker 스레드에서만 호출된다(UI 스레드 네트워크 호출 제거).
                self.interrupt()
                raise InterruptedError("ComfyUI 이미지 생성이 취소되었습니다.")
            r = requests.get(self.base_url + f"/history/{prompt_id}", timeout=10)
            r.raise_for_status()
            history = r.json()
            if prompt_id in history:
                item = history[prompt_id]
                status = item.get("status") or {}
                # 오류 판정 조건을 각각 명시적으로 분리한다(연산자 우선순위 의존 제거).
                status_str = str(status.get("status_str") or "").strip().lower()
                completed = status.get("completed")
                messages = status.get("messages") or []
                if status_str == "error":
                    raise RuntimeError(f"ComfyUI workflow 실행 오류: {status}")
                if completed is False and (status_str != "success" or messages):
                    # history에는 기록됐으나 완료로 판정할 수 없는 상태는
                    # 타임아웃까지 무의미하게 대기하지 않는다.
                    if messages:
                        raise RuntimeError(f"ComfyUI workflow 오류 메시지: {messages}")
                    raise RuntimeError(f"ComfyUI workflow가 완료되지 않았습니다: {status}")
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
                # 종료 기록은 있으나 이미지 출력이 없으면 제한 횟수까지만 재확인한다.
                pending_polls += 1
                if pending_polls >= 4:
                    raise RuntimeError(
                        f"ComfyUI가 이미지를 반환하지 않았습니다 (status={status or '없음'})"
                    )
            time.sleep(poll)
        raise TimeoutError("ComfyUI 이미지 생성 시간이 초과되었습니다. (600초)")

    def list_checkpoints(self, timeout=5):
        """CheckpointLoaderSimple 노드가 요구하는 체크포인트 목록을 ComfyUI에서 조회한다."""
        r = requests.get(self.base_url + "/object_info/CheckpointLoaderSimple", timeout=timeout)
        r.raise_for_status()
        data = r.json()
        node = (data or {}).get("CheckpointLoaderSimple") or {}
        values = ((node.get("input") or {}).get("required") or {}).get("ckpt_name")
        if not isinstance(values, list) or not values:
            return []
        options = values[0]
        return [str(v) for v in options] if isinstance(options, list) else []

    def download_image(self, filename, subfolder="", image_type="output"):
        params = {"filename": filename, "subfolder": subfolder, "type": image_type}
        r = requests.get(self.base_url + "/view", params=params, timeout=30)
        r.raise_for_status()
        return r.content

    _MIME_BY_SUFFIX = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }

    def upload_image(self, path, timeout=60):
        """이미지를 ComfyUI input 폴더에 업로드하고 LoadImage용 이름을 반환한다."""
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise ValueError(f"업로드할 이미지 파일을 찾을 수 없습니다: {p}")
        if p.stat().st_size == 0:
            raise ValueError(f"이미지 파일이 비어 있습니다: {p}")
        mime = self._MIME_BY_SUFFIX.get(p.suffix.lower())
        if mime is None:
            supported = ", ".join(sorted(self._MIME_BY_SUFFIX))
            raise ValueError(f"지원하지 않는 이미지 형식입니다: {p.suffix} (지원: {supported})")
        with p.open("rb") as f:
            r = requests.post(
                self.base_url + "/upload/image",
                files={"image": (p.name, f, mime)},
                data={"overwrite": "true"},
                timeout=timeout,
            )
        r.raise_for_status()
        data = r.json()
        name = data.get("name")
        if not name:
            raise RuntimeError(f"ComfyUI 이미지 업로드 실패: {data}")
        return name
