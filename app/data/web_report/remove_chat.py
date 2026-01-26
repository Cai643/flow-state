import requests
import os
import uuid

api_key = 'sk-Gwhx0iMED0qlkQS6Oxsuxo5DW192U-w28AM1JDEJsDk'
url = "http://localhost:7860/api/v1/run/09733a7e-ecf8-4771-b3fd-d4a367d67f57"  # The complete API endpoint URL for this flow

# Request payload configuration
payload = {
    "output_type": "chat",
    "input_type": "chat",
    "input_value": "hello world!"
}
payload["session_id"] = str(uuid.uuid4())

headers = {"x-api-key": api_key}

try:
    # Send API request
    response = requests.request("POST", url, json=payload, headers=headers)
    response.raise_for_status()  # Raise exception for bad status codes

    # Print response
    # 1. 解析 JSON 数据
    data = response.json()
    
    # 2. 提取核心回复 (就像剥洋葱一样找到最里面的 text)
    try:
        ai_reply = data["outputs"][0]["outputs"][0]["results"]["message"]["text"]
        print("--------------------------------------------------")
        print("🤖 AI 说:", ai_reply)
        print("--------------------------------------------------")
    except (KeyError, IndexError):
        # 万一数据结构变了，防止报错，还是打印原始数据
        print("⚠️ 无法提取精简回复，原始数据如下：")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"Error making API request: {e}")
except ValueError as e:
    print(f"Error parsing response: {e}")