import json, subprocess, sys
sys.path.insert(0, '.')
from runner import MMOClient

with open('state.json') as f:
    s = json.load(f)
token = s['session']['token']
sid = s['session']['sessionId']

client = MMOClient(token, sid)
client.start()
if not client.wait_for_auth(timeout=10):
    print('Auth failed')
    client.stop()
else:
    ws = client.get_world_state(timeout=15)
    user_id = s['commander']['userId']
    scout = next((u for u in ws.get('units', []) if u.get('ownerId') == user_id and u.get('type') == 'Scout'), None)
    scout_id = scout['id']
    print(f'Scout at ({scout["position"]["q"]},{scout["position"]["r"]}) HP={scout["currentHp"]} abilities:')
    for ab in scout.get('abilities', []):
        print(f'  {ab["name"]} cooldown={ab["currentCooldown"]} typeId={ab["abilityTypeId"]}')
    
    # Use Sensor Sweep (abilityTypeId 1)
    print('\nUsing Sensor Sweep...')
    client._send({'type': 'mmo_use_ability', 'payload': {
        'unitId': scout_id,
        'abilityTypeId': 1
    }})
    result = client.wait_for('mmo_ability_used', timeout=10)
    print(f'Sensor sweep result: {result}')
    
    # After sensor sweep, check world state again
    ws2 = client.get_world_state(timeout=15)
    asteroids = ws2.get('asteroids', [])
    units = ws2.get('units', [])
    edf = [u for u in units if u.get('ownerName') == 'Earth Defense Force']
    print(f'\nAfter Sensor Sweep:')
    print(f'  Asteroids: {len(asteroids)}')
    print(f'  EDF units: {len(edf)}')
    for a in asteroids[:10]:
        pos = a.get('position', {})
        print(f'    Asteroid {a["id"][:20]} at ({pos.get("q")},{pos.get("r")}) level={a.get("miningLevel")} depleted={a.get("isDepleted")}')
    for e in edf[:5]:
        pos = e.get('position', {})
        print(f'    EDF {e["type"]} at ({pos.get("q")},{pos.get("r")}) HP={e.get("currentHp")}')
    
    # Check chunks for asteroid data
    chunks = ws2.get('chunks', {})
    print(f'  World chunks: {len(chunks)}')
    for k, c in chunks.items():
        if c.get('asteroids', 0) > 0:
            print(f'    Chunk {k}: {c["asteroids"]} asteroids')
            print(f'    {json.dumps(c)[:300]}')
    
    client.stop()