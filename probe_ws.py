#!/usr/bin/env python3
"""Quick WS probe — test sensor sweep + movement toward Mars"""
import json, websocket, time

d = json.load(open('state.json'))
token = d['session']['token']

def probe():
    results = []

    def on_open(ws):
        ws.send(json.dumps({"type": "auth", "token": token}))
        time.sleep(0.3)
        ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))

    collected = {"world": None, "msg_types": []}
    world_done = False

    def on_msg(ws, msg):
        global collected, world_done
        try:
            data = json.loads(msg)
            t = data.get("type", "")
            p = data.get("payload", {})
            if t and t != "mmo_tick":
                collected["msg_types"].append(t)
                print(f"MSG: {t}", flush=True)
            if t == "mmo_world_state" and not world_done:
                chunks = p.get("chunks", [])
                units = [u for c in chunks for u in c.get("units", [])]
                our = [u for u in units if u.get("ownerId") == d["commander"]["userId"]]
                edf = [u for u in units if u.get("ownerName") == "Earth Defense Force"]
                asteroids = [a for c in chunks for a in c.get("asteroids", [])]
                print(f"WORLD: {len(units)} units, {len(asteroids)} asteroids, {len(edf)} EDF", flush=True)
                for e in edf[:5]:
                    print(f"  EDF: {e['type']} at ({e['position']}) HP={e['currentHp']}", flush=True)
                for a in asteroids[:10]:
                    print(f"  Ast: {a.get('id')} variant={a.get('variant')} min={a.get('mineralComposition')}", flush=True)
                world_done = True
            if t == "mmo_world_joined":
                print("Joined world", flush=True)
                # Try sensor sweep
                ws.send(json.dumps({
                    "type": "mmo_use_ability",
                    "payload": {
                        "unitId": "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_1",
                        "abilityTypeId": 1
                    }
                }))
                print("Sensor sweep sent", flush=True)
                # Try move toward Mars (12,-5)
                ws.send(json.dumps({
                    "type": "mmo_move_unit",
                    "payload": {
                        "unitId": "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_1",
                        "targetHex": {"q": 20, "r": -20}
                    }
                }))
                print("Move toward Mars sent", flush=True)
        except Exception as e:
            print(f"Err: {e}", flush=True)

    ws = websocket.WebSocketApp('wss://crimsonmandate.com/ws', on_open=on_open, on_message=on_msg)
    ws.run_forever(ping_interval=15, ping_timeout=10)

probe()