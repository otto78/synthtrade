"""Test OKX orders-algo-history endpoint to check actualSide field."""
import time
import hashlib
import hmac
import base64
import httpx
import json

OKX_BASE = "https://eea.okx.com"
API_KEY = "6dc066cc-eb44-4cd4-9a8d-64cb5f554e2f"
SECRET = "2884B473BC907337694A6AA72E30078F"
PASSPHRASE = "SynthTrade2026!"

def sign(timestamp: str, method: str, path: str, body: str = "") -> str:
    msg = timestamp + method + path + body
    mac = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

def get_server_time_ms() -> str:
    """Get OKX server time and return as ISO 8601 string."""
    r = httpx.get(OKX_BASE + "/api/v5/public/time", timeout=5)
    data = r.json()
    ts_ms = int(data["data"][0]["ts"])
    # Convert ms to ISO 8601
    import datetime
    dt = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts_ms % 1000:03d}Z"

def okx_get(path: str, params: dict = None) -> dict:
    ts = get_server_time_ms()
    url = OKX_BASE + path
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        full_path = path + "?" + qs
    else:
        full_path = path
        qs = ""
    
    sig = sign(ts, "GET", full_path)
    headers = {
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": sig,
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json",
    }
    r = httpx.get(url, params=params, headers=headers, timeout=10)
    return r.json()

# 1. Query orders-algo-history with the specific bracket_id (algoId)
print("=" * 80)
print("TEST 1: orders-algo-history with specific algoId=3759483174750236672")
print("=" * 80)
result = okx_get("/api/v5/trade/orders-algo-history", {"ordType": "oco", "algoId": "3759483174750236672"})
print(f"Code: {result.get('code')}, Msg: {result.get('msg', '')}")
for item in result.get("data", []):
    print(json.dumps(item, indent=2))

# 2. Also check the TP trade bracket 3745204575738245120
print()
print("=" * 80)
print("TEST 2: orders-algo-history with algoId=3745204575738245120 (known TP)")
print("=" * 80)
result2 = okx_get("/api/v5/trade/orders-algo-history", {"ordType": "oco", "algoId": "3745204575738245120"})
print(f"Code: {result2.get('code')}, Msg: {result2.get('msg', '')}")
for item in result2.get("data", []):
    print(json.dumps(item, indent=2))

# 3. Also check the current open trade bracket 3762133804690157568
print()
print("=" * 80)
print("TEST 3: orders-algo-history with algoId=3762133804690157568 (current open)")
print("=" * 80)
result3 = okx_get("/api/v5/trade/orders-algo-history", {"ordType": "oco", "algoId": "3762133804690157568"})
print(f"Code: {result3.get('code')}, Msg: {result3.get('msg', '')}")
for item in result3.get("data", []):
    print(json.dumps(item, indent=2))
