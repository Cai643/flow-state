import os
import uuid
import requests

class LangflowClient:
    def __init__(self, timeout: int = 30):
        self.summary_url = os.getenv('LANGFLOW_SUMMARY_URL', 'http://localhost:7860/api/v1/run/09733a7e-ecf8-4771-b3fd-d4a367d67f57')
        self.summary_key = os.getenv('LANGFLOW_SUMMARY_KEY', 'sk-BIuKrx5-d4ebcTn_8u-3XFAXljh4Jp-pgm6lR1FVAmY')
        self.enc_url = os.getenv('LANGFLOW_ENC_URL', 'http://localhost:7860/api/v1/run/7886edbe-e56a-46b5-ae24-9103becf35f1')
        self.enc_key = os.getenv('LANGFLOW_ENC_KEY', 'sk-BIuKrx5-d4ebcTn_8u-3XFAXljh4Jp-pgm6lR1FVAmY')
        self.detect_url = os.getenv('LANGFLOW_DETECT_URL', 'http://localhost:7860/api/v1/run/f45b7d1f-c583-4327-9093-6bfc75f20344')
        self.detect_key = os.getenv('LANGFLOW_DETECT_KEY', 'sk-BIuKrx5-d4ebcTn_8u-3XFAXljh4Jp-pgm6lR1FVAmY')
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
