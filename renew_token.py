#!/opt/homebrew/bin/python3
"""Crimson Mandate token renewer — stdlib only, no venv, no agent overhead."""
import json, urllib.request, urllib.error, os, datetime as dt

BASE = "https://crimsonmandate.com"
EMAIL = "halp@burk-dashboards.com"
PASSWORD = "Test1234!"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
LOG_FILE = "/Users/jonathan/.openclaw/workspace/reports/crimson-token-renewal.log"
USER_AGENT = "curl/8.1.2"

def login(email, password):
    data = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/auth/login",
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("success"):
                return result["data"], None
            return None, "login returned success=false"
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        return None, f"HTTP {e.code}: {body}"
    except Exception as e:
        return None, str(e)

def main():
    result, err = login(EMAIL, PASSWORD)
    if err or not result:
        ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{ts}] FAILED: {err}\n")
        print(f"FAILED: {err}")
        exit(1)

    token = result["token"]
    session_id = result["sessionId"]

    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except Exception:
        state = {}

    state["session"] = {"token": token, "sessionId": session_id}

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOG_FILE, "a") as f:
        f.write(f"Token renewed at {ts} session={session_id[:8]}\n")

    print(f"OK: session={session_id[:8]}...")

if __name__ == "__main__":
    main()