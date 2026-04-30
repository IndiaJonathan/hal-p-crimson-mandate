#!/usr/bin/env python3
"""Move HALP scout to Mars (12,-5) and attempt mining"""
import sys, os, time, json
sys.path.insert(0, '/Users/jonathan/.openclaw/workspace/crimson-mandate-agent')

from runner import MMOClient, api_get
from memory import load_state

AGENT_DIR = '/Users/jonathan/.openclaw/workspace/crimson-mandate-agent'

# Updated respawn ID from latest scan
HALP_SCOUT_ID = "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_respawn_95d47346"
MARS = {"q": 12, "r": -5}

def hex_distance(a, b):
    q1, r1 = a.get('q', 0), a.get('r', 0)
    q2, r2 = b.get('q', 0), b.get('r', 0)
    return max(abs(q1-q2), abs(r1-r2), abs((q1+r1)-(q2+r2)))

print("=" * 60)
print("HALP Scout -> Mars (12,-5) -- CRITICAL MOVE")
print("=" * 60)

halp_state = load_state()
token = halp_state.get("session", {}).get("token", "")
session_id = halp_state.get("session", {}).get("sessionId", "")

if not token:
    print("ERROR: No token.")
    sys.exit(1)

# Step 1: Move to Mars
print("\n[Step 1] Moving scout to Mars (12,-5)...")
c = MMOClient(token, session_id)
c.start()
if not c.wait_for_auth(timeout=10):
    print("WS auth failed")
    c.stop()
    sys.exit(1)

_ = c.get_world_state(timeout=10)
c._send({"type": "mmo_move_unit", "payload": {
    "unitId": HALP_SCOUT_ID,
    "targetHex": MARS
}})
events = c.wait_for("mmo_unit_moved", timeout=15)
if events:
    print("  OK: Moved to Mars!")
else:
    print("  WARN: No move confirmation")
c.stop()

time.sleep(2)

# Step 2: Mine!
print("\n[Step 2] Attempting to mine...")
c2 = MMOClient(token, session_id)
c2.start()
mining_ok = False
if c2.wait_for_auth(timeout=8):
    ws = c2.get_world_state(timeout=10)
    c2._send({"type": "mmo_mine_asteroid", "payload": {
        "unitId": HALP_SCOUT_ID,
        "targetPosition": MARS
    }})
    time.sleep(5)
    # Check for mining result
    mining_events = c2.wait_for("mmo_mine_result", timeout=10)
    error_events = c2.wait_for("error", timeout=5)
    
    print("  Mining events: " + str(mining_events))
    print("  Error events: " + str(error_events))
    
    if mining_events:
        mining_ok = True

    c2.stop()
else:
    c2.stop()
    print("  Auth failed")

time.sleep(2)

# Step 3: Check post-mine world state
print("\n[Step 3] Checking post-mine world state...")
c3 = MMOClient(token, session_id)
c3.start()
if c3.wait_for_auth(timeout=8):
    ws3 = c3.get_world_state(timeout=15)
    asteroids = ws3.get("asteroids", [])
    units = ws3.get("units", [])
    planets = ws3.get("planets", [])
    
    halp_pos = None
    for u in units:
        if u.get("id") == HALP_SCOUT_ID:
            halp_pos = u.get("position", {})
            break
    
    print("  HALP position: (" + str(halp_pos.get('q')) + "," + str(halp_pos.get('r')) + ")")
    print("  Asteroids visible: " + str(len(asteroids)))
    for a in asteroids[:10]:
        pos = a.get("position", {})
        own = a.get("ownerName", "NONE")
        print("    asteroid at (" + str(pos.get('q')) + "," + str(pos.get('r')) + ") type=" + str(a.get('type')) + " owner=" + str(own))
    
    # Check balance
    bal = api_get("/api/balance", token)
    print("\n  Balance: " + str(bal))
    
    c3.stop()
else:
    print("  Auth failed on check")

print("\nDone.")