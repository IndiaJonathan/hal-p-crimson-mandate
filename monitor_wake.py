#!/usr/bin/env python3
"""
Crimson Mandate — Active Monitor (HAL-P eyes on glass every 5 min)
Wakes HAL-P main session with instructions to review, decide, act.
"""
import json, urllib.request, time

SESSION_KEY = "agent:main:discord:direct:148191845040652288"
OPENCLAW_BASE = "http://localhost:18789"

DIRECTIVE = """You are MONITORING Crimson Mandate. Read these files first:
1. /Users/jonathan/.openclaw/workspace/crimson-mandate-agent/operator.log (last 50 lines)
2. /Users/jonathan/.openclaw/workspace/crimson-mandate-agent/state.json
3. /Users/jonathan/.openclaw/workspace/crimson-mandate-agent/improvement_log.md (last 30 lines)

Then make decisions:
- Is the operator running OK? Any new errors?
- Has game state changed? New fighters? Golden asteroid?
- Does the operator code need a subagent to fix something?
- Write a status note to /Users/jonathan/.openclaw/workspace/crimson-mandate-agent/MONITOR_NOTES.md (append today's timestamp + findings)
- If significant event (fighter kill, golden asteroid, ISD milestone, deadlock broken): message Jonathan on Discord
- If code fix needed: spawn a subagent immediately
- If nothing urgent: just update MONITOR_NOTES.md and exit silently

Stay concise. Write findings to MONITOR_NOTES.md. Do not send Jonathan a message unless something meaningful happened.
"""

try:
    # Find main session
    req = urllib.request.Request(
        f"{OPENCLAW_BASE}/api/sessions",
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        sessions = json.loads(resp.read())

    session_key = None
    for s in sessions:
        if s.get("kind") == "main":
            session_key = s.get("sessionKey") or s.get("key")
            break

    if not session_key:
        print("No main session found")
        exit(1)

    data = json.dumps({"content": DIRECTIVE.strip()}).encode()
    req = urllib.request.Request(
        f"{OPENCLAW_BASE}/api/sessions/{session_key}/messages",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(f"Wake-up sent to HAL-P main session")
except Exception as e:
    print(f"Error: {e}")
    exit(1)
