import requests

class LMStudioClient:
    def __init__(self, settings):
        self.settings = settings

    @property
    def base_url(self):
        s = self.settings
        return f"http://{s.get('host','127.0.0.1')}:{int(s.get('port',1234))}{s.get('api_path','/v1').rstrip('/')}"

    def test_connection(self, timeout=3):
        r = requests.get(self.base_url + "/models", timeout=timeout)
        r.raise_for_status()
        return r.json()

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
        content = r.json()["choices"][0]["message"]["content"]
        return __import__("json").loads(content)
