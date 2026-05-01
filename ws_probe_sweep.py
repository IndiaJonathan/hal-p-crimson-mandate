#!/usr/bin/env python3
"""Move HALP Scout toward Mars + check world state"""
import json, websocket, time

with open("state.json") as f:
    state = json.load(f)
token = state["session"]["token"]

SCOUT_ID = "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_respawn_f696459e"
MARS_TARGET = (12, -5)
START_POS = (2, 0)

def cube_dist(p1, p2):
    def cube(q, r): return (q, -q-r, r)
    c1 = cube(p1[0], p1[1])
    c2 = cube(p2[0], p2[1])
    return max(abs(c1[i]-c2[i]) for i in range(3))

def on_msg(ws, msg):
    try:
        data = json.loads(msg)
        t = data.get("type", "")
        p = data.get("payload", {})
        if t == "mmo_world_state":
            chunks = p.get("chunks", [])
            units_all = [u for c in chunks for u in c.get("units", [])]
            our = [u for u in units_all if u.get("ownerId") and "0a8a2ff5" in u.get("ownerId", "")]
            edf = [u for u in units_all if u.get("ownerName") == "Earth Defense Force"]
            asteroids = [a for c in chunks for a in c.get("asteroids", [])]
            print(f"WORLD: {len(units_all)} units, {len(asteroids)} asteroids, {len(edf)} EDF")
            if our:
                for u in our:
                    print(f"  OUR: {u['type']} at ({u.get('position')}) HP={u.get('currentHp')}")
            for a in asteroids[:5]:
                print(f"  Ast: {a.get('variant')} at {a.get('position')} min={a.get('mineralComposition')}")
            for e in edf[:5]:
                print(f"  EDF: {e['type']} at {e.get('position')} HP={e.get('currentHp')}")
        elif t == "mmo_unit_moved":
            print(f"MOVED: to ({p.get('position')})")
        elif t == "mmo_golden_asteroid_spawned":
            print(f"GOLDEN ASTEROID at {p.get('position')}!")
        elif t == "mmo_resources":
            print(f"ISD: {p.get('isdBalance')} | Credits: {p.get('credits')}")
        elif t not in ("mmo_tick", "mmo_pong"):
            print(f"MSG: {t}: {str(p)[:200]}")
    except Exception as e:
        print(f"ERR: {e}")

def on_open(ws):
    ws.send(json.dumps({"type": "auth", "token": token}))
    time.sleep(0.5)
    ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
    time.sleep(2)
    # Move one step toward Mars
    ws.send(json.dumps({
        "type": "mmo_move_unit",
        "payload": {
            "unitId": SCOUT_ID,
            "targetHex": {"q": 3, "r": -1}
        }
    }))
    print(f"Sent move to (3,-1)")

ws = websocket.WebSocketApp("wss://crimsonmandate.com/ws", on_message=on_msg)
ws.on_open = on_open
ws.run_forever(ping_interval=15, ping_timeout=10)
