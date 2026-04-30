#!/usr/bin/env python3
"""Move HALP scout and check world state"""
import json, requests, time

with open('/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/state.json') as f:
    state = json.load(f)

token = state['session']['token']
headers = {"Authorization": f"Bearer {token}"}
BASE = "https://crimsonmandate.com"

# Find HALP scout unit (ownerId = 0a8a2ff5-1b93-44c3-994c-6891e0076d72)
units = state.get('units', [])
halp_scout = None
for u in units:
    if u.get('ownerId') == '0a8a2ff5-1b93-44c3-994c-6891e0076d72':
        halp_scout = u
        break

if not halp_scout:
    print("HALP scout NOT FOUND in state")
    print("All owners:", sorted(set(u.get('ownerId','?') for u in units)))
else:
    print(f"HALP Scout: {halp_scout['id']}")
    print(f"Position: {halp_scout.get('position')}")
    print(f"Type: {halp_scout.get('type')}")
    unit_id = halp_scout['id']

    # Current position: q=28, r=-31
    # Mars target: q=12, r=-5
    # Direction: delta = (-16, +26) → move west/southwest
    # Move direction [-1, 0] (west)
    move_resp = requests.post(f"{BASE}/api/game/move", json={
        "unitId": unit_id,
        "direction": [-1, 0]
    }, headers=headers, timeout=15)
    print(f"\nMOVE response: {move_resp.status_code}")
    print(move_resp.text[:400])

time.sleep(3)

# Get world state
ws_resp = requests.get(f"{BASE}/api/game/world-state", headers=headers, timeout=15)
try:
    ws = ws_resp.json()
    print(f"\nWS success, keys: {list(ws.keys())}")
except:
    print("WS parse failed:", ws_resp.text[:200])
    ws = {}

chunks = ws.get('chunks', [])
print(f"Chunks returned: {len(chunks)}")
for c in chunks:
    a_count = len(c.get('asteroids', []))
    if a_count > 0:
        print(f"  Chunk ({c.get('q')},{c.get('r')}): {a_count} asteroids")
        for a in c.get('asteroids', [])[:3]:
            print(f"    Asteroid: id={a.get('id')} pos={a.get('position')} golden={a.get('golden')}")

vision = ws.get('currentVision', [])
print(f"\nCurrent vision entries: {len(vision)}")
for v in vision[:10]:
    print(f"  {v.get('type')} at {v.get('position')} golden={v.get('golden')}")

fog = ws.get('fogOfWar', [])
print(f"Fog of war entries: {len(fog)}")

# Units in WS
units_ws = ws.get('units', [])
print(f"\nUnits in WS: {len(units_ws)}")
for u in units_ws:
    if u.get('ownerId') == '0a8a2ff5-1b93-44c3-994c-6891e0076d72':
        pos = u.get('position', {})
        print(f"HALP scout now at: q={pos.get('q')}, r={pos.get('r')}")
        with open('/tmp/crimson_halp_pos.txt', 'w') as f:
            f.write(f"{pos.get('q')},{pos.get('r')}")