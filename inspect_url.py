import time
import requests

def check_url(name, url, method="GET", timeout=5):
    start = time.time()
    try:
        if method.upper() == "POST":
            resp = requests.post(url, timeout=timeout)
        else:
            resp = requests.get(url, timeout=timeout)

        cost = round(time.time() - start, 3)

        if resp.status_code == 200:
            return {
                "type": "url",
                "name": name,
                "target": url,
                "ok": True,
                "detail": "HTTP 200",
                "cost": cost
            }
        else:
            return {
                "type": "url",
                "name": name,
                "target": url,
                "ok": False,
                "detail": f"HTTP {resp.status_code}",
                "cost": cost
            }

    except Exception as e:
        return {
            "type": "url",
            "name": name,
            "target": url,
            "ok": False,
            "detail": str(e),
            "cost": None
        }
