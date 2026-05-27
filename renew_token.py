#!/usr/bin/env python3
"""Standalone token renewal for Crimson Mandate — no venv deps needed."""
import json, urllib.request, urllib.error, os

BASE = "https://crimsonmandate.com"
STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")
EMAIL = "halp@burk-dashboards.com"
PASSWORD = "Test1234!"
LOG_FILE = "/Users/jonathan/.openclaw/workspace/reports/crimson-token-renewal.log"

def login(email, password):
    data = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/auth/login",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("success"):
                return result["data"]
    except Exception as e:
        print(f"Login error: {e}")
    return None

def main():
    result = login(EMAIL, PASSWORD)
    if not result:
        print("FAILED: login call unsuccessful")
        exit(1)

    token = result["token"]
    session_id = result["sessionId"]

    # Load existing state, preserve everything except session
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except Exception:
        state = {}

    state["session"] = {"token": token, "sessionId": session_id}

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    ts = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOG_FILE, "a") as f:
        f.write(f"Token renewed at {ts}\n")

    print(f"OK: session={session_id[:8]}..., state updated")

if __name__ == "__main__":
    main()