import os
import uuid
import requests

class LangflowClient:
    def __init__(self, timeout: int = 180):
        self.summary_url = os.getenv('LANGFLOW_SUMMARY_URL', 'http://localhost:7860/api/v1/run/9608210a-cdbb-4c53-879f-8b37984d6d9b')
        self.summary_key = os.getenv('LANGFLOW_SUMMARY_KEY', 'sk-ivJj5oRPiiUD51xPwM6qPERLLedQM6qzW9YZcDUKUm8')
        self.enc_url = os.getenv('LANGFLOW_ENC_URL', 'http://localhost:7860/api/v1/run/9608210a-cdbb-4c53-879f-8b37984d6d9b')
        self.enc_key = os.getenv('LANGFLOW_ENC_KEY', 'sk-ivJj5oRPiiUD51xPwM6qPERLLedQM6qzW9YZcDUKUm8')
        self.detect_url = os.getenv('LANGFLOW_DETECT_URL', 'http://localhost:7860/api/v1/run/9608210a-cdbb-4c53-879f-8b37984d6d9b')
        self.detect_key = os.getenv('LANGFLOW_DETECT_KEY', 'sk-ivJj5oRPiiUD51xPwM6qPERLLedQM6qzW9YZcDUKUm8')
        self.timeout = timeout

    def call_flow(self, flow: str, text: str):
        if flow == 'summary':
            url, key = self.summary_url, self.summary_key
        elif flow == 'enc':
            url, key = self.enc_url, self.enc_key
        else:
            url, key = self.detect_url, self.detect_key
        try:
            resp = requests.post(
                url,
                json={"input_value": text, "input_type": "chat", "output_type": "chat", "session_id": str(uuid.uuid4())},
                headers={"x-api-key": key} if key else {},
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            return self._extract_text(data)
        except Exception:
            return None

    def _extract_text(self, data):
        try:
            return data["outputs"][0]["outputs"][0]["results"]["message"]["text"]
        except Exception:
            pass
        try:
            return data.get("text") or data.get("message", {}).get("text")
        except Exception:
            pass
        try:
            return str(data)
        except Exception:
            return None
