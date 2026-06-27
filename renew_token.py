#!/usr/bin/env python3
"""
Token renewal script for Crimson Mandate operator.
Run auth.py to get a fresh JWT, then save to state.json.
"""
import json
import sys
import subprocess
import os

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(AGENT_DIR, "state.json")

def main():
    # Run auth.py to get fresh token
    result = subprocess.run(
        [sys.executable, "auth.py"],
        cwd=AGENT_DIR,
        capture_output=True,
        text=True,
        timeout=30
    )
    if result.returncode != 0:
        print(f"auth.py failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    
    # Read current state
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
    
    # Read new token from auth output (last line that looks like a JWT)
    for line in reversed(result.stdout.strip().split("\n")):
        line = line.strip()
        if line.startswith("eyJ") and "." in line:
            # This is a JWT
            import jwt
            decoded = jwt.decode(line, options={"verify_signature": False})
            new_session_id = decoded.get("sessionId", "unknown")
            new_exp = decoded.get("exp", 0)
            state["session"]["token"] = line
            state["session"]["sessionId"] = new_session_id
            with open(STATE_FILE, "w") as f:
                json.dump(state, f)
            print(f"Token renewed. Exp: {new_exp}")
            return
    
    print("No JWT found in auth.py output", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
