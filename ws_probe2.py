#!/usr/bin/env python3
"""WS probe - manual receive loop"""
import json, websocket, time

d = json.load(open('state.json'))
token = d['session']['token']

print("Opening WS...", flush=True)
ws = websocket.create_connection("wss://crimsonmandate.com/ws", timeout=15)
print("WS connected", flush=True)

ws.send(json.dumps({"type": "auth", "token": token}))
print("Auth sent", flush=True)

# Receive until we get world_state or timeout
end = time.time() + 20
while time.time() < end:
    msg = ws.recv()
    if msg:
        data = json.loads(msg)
        t = data.get("type", "")
        p = data.get("payload", {})
        print(f"MSG: {t}", flush=True)
        if t == "auth_success":
            print("AUTH OK - sending join_world", flush=True)
            ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
        elif t == "mmo_world_state":
            chunks = p.get("chunks", [])
            units = [u for c in chunks for u in c.get("units", [])]
            our = [u for u in units if u.get("ownerId") == d["commander"]["userId"]]
            edf = [u for u in units if u.get("ownerName") == "Earth Defense Force"]
            asteroids = [a for c in chunks for a in c.get("asteroids", [])]
            print(f"WORLD: {len(units)} units, {len(our)} ours, {len(edf)} EDF, {len(asteroids)} asteroids", flush=True)
            for u in our:
                print(f"  Our {u['type']} at ({u['position']['q']},{u['position']['r']})", flush=True)
            for e in edf[:5]:
                print(f"  EDF {e['type']} at ({e['position']['q']},{e['position']['r']}) HP={e['currentHp']}", flush=True)
            for a in asteroids[:10]:
                mc = a.get('mineralComposition', {})
                print(f"  Ast {a.get('variant')} iron={mc.get('min_iron',0)} copper={mc.get('min_copper',0)} at ({a.get('position',{}).get('q')},{a.get('position',{}).get('r')})", flush=True)
            break
        elif t == "error":
            print(f"ERROR: {p}", flush=True)
    time.sleep(0.1)

ws.close()
print("Done", flush=True)