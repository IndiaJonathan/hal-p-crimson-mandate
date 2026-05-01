#!/usr/bin/env python3
"""Single-shot probe: auth, move toward Mars, check world state."""
import json, websocket, time, sys
sys.path.insert(0, '.')
from runner import MMOClient

with open('/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/state.json') as f:
    s = json.load(f)
token = s['session']['token']
sid = s['session']['sessionId']
user_id = s['commander']['userId']

SCOUT_ID = "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_1"
MARS = {"q": 12, "r": -5}

client = MMOClient(token, sid)
client.start()
if not client.wait_for_auth(timeout=10):
    print('Auth failed')
    client.stop()
    sys.exit(1)

ws = client.get_world_state(timeout=15)
# Find HALP scout position
units = ws.get('units', [])
halp = next((u for u in units if u.get('ownerId') == user_id and u.get('type') == 'Scout'), None)
if halp:
    print(f'HALP at ({halp["position"]["q"]},{halp["position"]["r"]}) HP={halp["currentHp"]}')
else:
    # Try from state.json directly
    for u in s.get('units', []):
        if u.get('ownerName') == 'halp':
            print(f'HALP from state at ({u["position"]["q"]},{u["position"]["r"]})')

# Move toward Mars using mmo_move_unit with targetHex
print(f'\nMoving toward Mars {MARS}...')
client._send({
    "type": "mmo_move_unit",
    "payload": {
        "unitId": SCOUT_ID,
        "targetHex": MARS
    }
})

# Wait for move confirmation
result = client.wait_for('mmo_unit_moved', timeout=10)
print(f'Move result: {result}')

time.sleep(2)

# Check new position
ws2 = client.get_world_state(timeout=15)
units2 = ws2.get('units', [])
halp2 = next((u for u in units2 if u.get('ownerId') == user_id and u.get('type') == 'Scout'), None)
if halp2:
    print(f'HALP now at ({halp2["position"]["q"]},{halp2["position"]["r"]})')
else:
    print('HALP scout not found in world state after move')

# Check for golden asteroids
chunks = ws2.get('chunks', {})
asteroids = [a for c in chunks.values() for a in c.get('asteroids', [])]
golden = [a for a in asteroids if a.get('variant') == 'golden']
print(f'Asteroids visible: {len(asteroids)}')
print(f'Golden asteroids: {len(golden)}')
for a in golden:
    print(f'  GOLDEN: {a["id"]} at ({a["position"]})')

client.stop()
print('Done')