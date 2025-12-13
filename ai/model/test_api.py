import json
import time
from urllib import request, error

BASE_URL = "http://127.0.0.1:5000/api/v1"

def http_json(method: str, url: str, body: dict | None = None, headers: dict | None = None):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = request.Request(url, data=data, method=method.upper())
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8") or "{}"
            return resp.getcode(), json.loads(content)
    except error.HTTPError as e:
        try:
            content = e.read().decode("utf-8")
            return e.code, json.loads(content)
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def wait_server(url: str, timeout: float = 10.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            code, _ = http_json("GET", "http://127.0.0.1:5000/")
            if code in (200, 404):
                return True
        except Exception:
            time.sleep(0.5)
    return False

def main():
    if not wait_server(BASE_URL):
        print("服务未就绪，请先运行 API 服务器: D:/python/python.exe e:/flow-state/ai/model/API.py")
        return

    username = "tester"
    password = "pass123"
    email = "tester@example.com"

    # 注册
    code, resp = http_json("POST", f"{BASE_URL}/auth/register", {
        "username": username,
        "password": password,
        "email": email
    })
    print("register:", code, resp)

    # 登录
    code, resp = http_json("POST", f"{BASE_URL}/auth/login", {
        "username": username,
        "password": password
    })
    print("login:", code, resp)
    if code != 200:
        print("登录失败，退出")
        return

    token = resp.get("token") if isinstance(resp, dict) else None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 页面识别
    code, resp = http_json("POST", f"{BASE_URL}/page/recognize", {"detailed": True}, headers=headers)
    print("recognize:", code, resp)

    # 视频学习质量示例
    sample_signals = {
        "isFullscreen": True,
        "hasSubtitles": True,
        "noteTaking": False,
        "pauseFrequency": 3,
        "playbackSpeed": 1.25
    }
    code, resp = http_json("POST", f"{BASE_URL}/video/learning-quality", {"videoSignals": sample_signals}, headers=headers)
    print("video quality:", code, resp)

if __name__ == "__main__":
    main()