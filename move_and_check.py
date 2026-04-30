#!/usr/bin/env python3
"""Move HALP scout one step toward Mars and check world state"""
import json, sys, os, requests, time

sys.path.insert(0, '/Users/jonathan/.openclaw/workspace/crimson-mandate-agent')

# Load auth
with open('/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/state.json') as f:
    state = json.load(f)
token = state["session"]["token"]
headers = {"Authorization": f"Bearer {token}"}

BASE = "https://crimsonmandate.com"

def api_get(path):
    r = requests.get(f"{BASE}{path}", headers=headers, timeout=10)
    return r.json()

def api_post(path, data):
    r = requests.post(f"{BASE}{path}", headers=headers, json=data, timeout=10)
    return r.json()

# Scout current position (2,0), Mars target (12,-5)
# Direction: x+1, y-1 each step
current_x, current_y = 2, 0
new_x, new_y = current_x + 1, current_y - 1  # toward Mars

print(f"=== HALP Scout Move {current_x},{current_y} → ({new_x},{new_y}) ===")
print(f"Moving toward Mars (target: 12,-5)")

# Get available units
units_resp = api_get("/api/units")
print(f"\nUnits response: {json.dumps(units_resp, indent=2)[:500]}")

# Find HALP scout
halp_scout = None
for unit in units_resp.get("data", []):
    if "respawn_f696459e" in unit.get("id", ""):
        halp_scout = unit
        break

if not halp_scout:
    print("ERROR: HALP scout not found!")
    sys.exit(1)

print(f"\nHALP Scout: {halp_scout['id']}")
print(f"  Position: ({halp_scout.get('x',0)}, {halp_scout.get('y',0)})")

# Move scout
move_resp = api_post("/api/units/move", {
    "unitId": halp_scout["id"],
    "x": new_x,
    "y": new_y
})
print(f"\nMove response: {json.dumps(move_resp, indent=2)}")

# Check world state for asteroids
print("\n=== World State Check ===")
ws = api_get("/api/world/state")
chunks = ws.get("data", {}).get("chunks", [])

asteroid_count = 0
edf_count = 0
vision_asteroids = []
vision_edf = []

for chunk in chunks:
    asteroid_count += len(chunk.get("asteroids", []))
    edf_count += len(chunk.get("enemies", []))
    for a in chunk.get("asteroids", []):
        vision_asteroids.append(a)
    for e in chunk.get("enemies", []):
        vision_edf.append(e)

print(f"Asteroids in world chunks: {asteroid_count}")
print(f"EDF fighters in world chunks: {edf_count}")

# Check fog of war and current vision
fog = ws.get("data", {}).get("fogOfWar", [])
vision = ws.get("data", {}).get("currentVision", [])
print(f"Fog of war entries: {len(fog)}")
print(f"Current vision entries: {len(vision)}")

# Check sensor sweep ability
print("\n=== Checking Ability: Sensor Sweep ===")
abilities_resp = api_get("/api/units/abilities")
print(f"Abilities response: {json.dumps(abilities_resp, indent=2)[:800]}")

# Store result
result = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M CDT"),
    "action": f"Move HALP scout ({current_x},{current_y}) → ({new_x},{new_y})",
    "move_result": move_resp,
    "asteroid_count": asteroid_count,
    "edf_count": edf_count,
    "fog_entries": len(fog),
    "vision_entries": len(vision),
    "new_position": f"({new_x},{new_y})"
}
print(f"\n=== RESULT ===")
print(json.dumps(result, indent=2))