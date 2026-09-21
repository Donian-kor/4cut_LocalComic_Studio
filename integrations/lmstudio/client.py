import json
import re
import requests


class LMStudioClient:
    def __init__(self, settings):
        self.settings = dict(settings)

    @property
    def base_url(self):
        s = self.settings
        host = str(s.get("host", "127.0.0.1")).strip()
        api = str(s.get("api_path", "/v1")).strip().rstrip("/") or "/v1"
        return f"http://{host}:{int(s.get('port', 1234))}{api}"

    def test_connection(self, timeout=3):
        r = requests.get(self.base_url + "/models", timeout=timeout)
        r.raise_for_status()
        return r.json()

    def list_models(self, timeout=3):
        r = requests.get(self.base_url + "/models", timeout=timeout)
        r.raise_for_status()
        data = r.json()
        items = data.get("data", []) if isinstance(data, dict) else data
        return [str(item["id"]) for item in items if isinstance(item, dict) and item.get("id")]

    def chat_json(self, system_prompt, user_prompt, timeout=180):
        payload = {
            "model": self.settings.get("model") or "local-model",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }
        r = requests.post(self.base_url + "/chat/completions", json=payload, timeout=timeout)
        r.raise_for_status()
        try:
            content = r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"LM Studio 응답 형식이 예상과 다릅니다: {e}") from e
        if not isinstance(content, str):
            raise ValueError("LM Studio의 content가 문자열이 아닙니다.")
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"LM Studio가 유효한 JSON을 반환하지 않았습니다: {e}") from e
