#!/usr/bin/env python3
"""Move HALP scout toward asteroid at (-12, 10) and do sensor sweep"""
import json, websocket, time, sys

d = json.load(open('state.json'))
token = d['session']['token']

# HALP's scout
UNIT_ID = "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_1"
# Asteroids from state:
# ast_86636ca4 at (-12, 10) - common_gold, titanium=9
# ast_e86df2a6 at (-12, 14) - common_gold, titanium=2
# Target: (-12, 10)

TARGET = {"q": -12, "r": 10}

out = []

def log(msg):
    print(msg, flush=True)
    out.append(msg)

done = False
moved = False

def on_open(ws):
    log("WS opened, authenticating...")
    ws.send(json.dumps({"type": "auth", "token": token}))
    time.sleep(0.3)
    ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
    log("join_world sent")

def on_msg(ws, msg):
    global done, moved
    try:
        data = json.loads(msg)
        t = data.get("type", "")
        p = data.get("payload", {})
        
        if t == "connected":
            log("WS connected")
        elif t == "auth_success":
            log("AUTH_SUCCESS")
        elif t == "mmo_world_state":
            chunks = p.get("chunks", [])
            units = [u for c in chunks for u in c.get("units", [])]
            our = [u for u in units if u.get("ownerId") == d["commander"]["userId"]]
            edf = [u for u in units if u.get("ownerName") == "Earth Defense Force"]
            asteroids = [a for c in chunks for a in c.get("asteroids", [])]
            log(f"WORLD: {len(units)} units, {len(our)} ours, {len(edf)} EDF, {len(asteroids)} asteroids")
            for u in our:
                log(f"  Our {u['type']} at ({u['position']['q']},{u['position']['r']}) HP={u['currentHp']}")
            for e in edf[:5]:
                log(f"  EDF {e['type']} at ({e['position']['q']},{e['position']['r']}) HP={e['currentHp']}")
            for a in asteroids[:10]:
                mc = a.get('mineralComposition', {})
                log(f"  Ast {a['id']} iron={mc.get('min_iron',0)} copper={mc.get('min_copper',0)} titanium={mc.get('min_titanium',0)} at ({a.get('position',{}).get('q')},{a.get('position',{}).get('r')}) variant={a.get('variant')}")
            # Sensor sweep first to see more
            ws.send(json.dumps({"type": "mmo_use_ability", "payload": {"unitId": UNIT_ID, "abilityTypeId": 1}}))
            log(f"SENSOR_SWEEP_SENT for {UNIT_ID}")
            time.sleep(0.5)
            # Move toward asteroid
            ws.send(json.dumps({"type": "mmo_move_unit", "payload": {"unitId": UNIT_ID, "targetHex": TARGET}}))
            log(f"MOVE_SENT to ({TARGET['q']},{TARGET['r']})")
        elif t == "mmo_unit_moved":
            log(f"MOVED_OK: {p.get('unitId')} -> ({p.get('position',{}).get('q')},{p.get('position',{}).get('r')})")
            moved = True
        elif t == "mmo_ability_activated":
            log(f"ABILITY_ACTIVATED: {p}")
        elif t == "mmo_golden_asteroid_spawned":
            log(f"!!! GOLDEN ASTEROID SPAWNED at {p.get('position')} !!!")
        elif t == "mmo_world_joined":
            log("WORLD_JOINED")
        elif t == "error":
            log(f"WS_ERROR: {p}")
    except Exception as e:
        log(f"Err: {e}")

ws = websocket.WebSocketApp('wss://crimsonmandate.com/ws', on_open=on_open, on_message=on_msg)
log("Starting WS...")
ws.run_forever(ping_interval=15, ping_timeout=10)
log("WS closed")
json.dump(out, open('/tmp/scout_move_out.json', 'w'))
