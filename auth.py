#!/usr/bin/env python3
"""
Authenticate and store session token for Crimson Mandate agent.
Usage: python3 auth.py <email> <password>
"""
import json, sys, requests

BASE = "https://crimsonmandate.com"
STATE_FILE = "state.json"

def login(email, password):
    resp = requests.post(
        f"{BASE}/api/auth/login",
        json={"email": email, "password": password},
        timeout=15
    )
    data = resp.json()
    if not data.get("success"):
        print(f"Login failed: {data}")
        return None
    return data["data"]

def main():
    email = sys.argv[1] if len(sys.argv) > 1 else "halp@burk-dashboards.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "Test1234!"
    
    print(f"Logging in as {email}...")
    result = login(email, password)
    if not result:
        sys.exit(1)
    
    token = result["token"]
    session_id = result["sessionId"]
    display_name = result.get("displayName", "?")
    
    # Load existing state
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
    except:
        state = {"commander": {}}
    
    state["session"] = {
        "token": token,
        "sessionId": session_id
    }
    state["commander"]["userId"] = result.get("userId", "")
    state["commander"]["displayName"] = display_name
    state["commander"]["email"] = email
    
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    
    print(f"✓ Authenticated as {display_name}")
    print(f"  Token: {token[:40]}...")
    print(f"  Session ID: {session_id}")
    print(f"  State saved to {STATE_FILE}")

if __name__ == "__main__":
    main()
