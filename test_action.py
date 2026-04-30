import requests, json, time

BASE = "https://api.ralphstar.online"
headers = {"Authorization": f"Bearer {open('.token').read().strip()}"}

# Move HALP scout toward Mars (12,-5): current pos (2,0) → direction [1,0] (east)
move_resp = requests.post(f"{BASE}/game/move", json={
    "unitId": "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_respawn_f696459e",
    "direction": [1, 0]
}, headers=headers)
print("MOVE:", move_resp.status_code, move_resp.text[:300])

time.sleep(2)

# Check world state
ws = requests.get(f"{BASE}/game/world-state", headers=headers).json()

asteroid_count = 0
chunk_data = []
for chunk_key in sorted(ws.get('chunks', {}).keys()):
    chunk = ws['chunks'][chunk_key]
    a_count = chunk.get('asteroidCount', 0)
    if a_count > 0:
        asteroid_count += a_count
        chunk_data.append(f"{chunk_key}: {a_count} asteroids")
    entities = chunk.get('entities', [])
    for e in entities:
        if e.get('type') == 'asteroid':
            asteroid_count += 1
            chunk_data.append(f"  Entity: {e}")

print(f"\nTotal asteroids visible: {asteroid_count}")
if chunk_data:
    for d in chunk_data[:10]:
        print(d)
else:
    print("No asteroids in any chunk")

vision = ws.get('currentVision', [])
print(f"\nCurrent vision entries: {len(vision)}")
for v in vision[:15]:
    print(f"  {v}")

fog = ws.get('fogOfWar', [])
print(f"\nFog of war entries: {len(fog)}")

units = ws.get('units', [])
halp_units = [u for u in units if 'respawn_f696459e' in u.get('unitId','')]
for u in halp_units:
    print(f"\nHALP Scout: pos={u.get('position')}, type={u.get('type')}")