#!/usr/bin/env python3
"""WS probe - get world state, move toward Mars, log everything"""
import json, websocket, time, sys, os

d = json.load(open('state.json'))
token = d['session']['token']
out = []

def log(msg):
    print(msg, flush=True)
    out.append(msg)

done = False
start = time.time()

def on_open(ws):
    log("WS opened, authenticating...")
    ws.send(json.dumps({"type": "auth", "token": token}))
    time.sleep(0.3)
    ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
    log("join_world sent")

def on_msg(ws, msg):
    global done
    elapsed = time.time() - start
    try:
        data = json.loads(msg)
        t = data.get("type", "")
        p = data.get("payload", {})
        log(f"[{elapsed:.1f}s] MSG: {t}")
        if t == "auth_success":
            log("AUTH_SUCCESS")
        elif t == "mmo_world_state" and not done:
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
                log(f"  Ast variant={a.get('variant')} iron={mc.get('min_iron',0)} copper={mc.get('min_copper',0)} gold={mc.get('min_gold',0)} at ({a.get('position',{}).get('q')},{a.get('position',{}).get('r')})")
            # Try sensor sweep
            ws.send(json.dumps({"type": "mmo_use_ability", "payload": {"unitId": "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_1", "abilityTypeId": 1}}))
            log("SENSOR_SWEEP_SENT")
            time.sleep(0.5)
            # Move toward Mars
            ws.send(json.dumps({"type": "mmo_move_unit", "payload": {"unitId": "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_1", "targetHex": {"q": 20, "r": -15}}}))
            log("MOVE_SENT to (20,-15)")
            done = True
        elif t == "mmo_unit_moved":
            log(f"MOVED_OK: unit={p.get('unitId')} new_pos={p.get('position')}")
        elif t == "mmo_ability_activated":
            log(f"ABILITY_ACTIVATED: {p}")
        elif t == "mmo_golden_asteroid_spawned":
            log(f"!!! GOLDEN !!! at {p.get('position')}")
        elif t == "mmo_world_joined":
            log("WORLD_JOINED")
        elif t == "error":
            log(f"WS_ERROR: {p}")
    except Exception as e:
        log(f"Err: {e}")

ws = websocket.WebSocketApp('wss://crimsonmandate.com/ws', on_open=on_open, on_message=on_msg)
log("Starting WS connection...")
ws.run_forever(ping_interval=15, ping_timeout=10)
log("WS connection closed")
json.dump(out, open('/tmp/ws_probe_out.json', 'w'))