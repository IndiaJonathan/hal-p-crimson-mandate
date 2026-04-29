#!/usr/bin/env python3
"""Move scout toward Mars + sensor sweep — one shot, capture results"""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

# Use halp token from state.json
d = json.load(open('state.json'))
token = d['session']['token']
scout_id = "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_1"
target  = {"q": 20, "r": -20}   # midpoint on path toward Mars (12,-5)

results = {}

def run():
    import websocket

    got_world = [False]
    moved = [False]
    swept = [False]
    ws = [None]

    def on_open(ws_app):
        ws_app.send(json.dumps({"type": "auth", "token": token}))
        ws_app.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))

    def on_msg(wsa, msg):
        try:
            data = json.loads(msg)
            t = data.get("type","")
            p = data.get("payload", {})

            if t == "mmo_world_joined":
                print("JOINED", flush=True)
                # Sensor sweep first
                wsa.send(json.dumps({
                    "type": "mmo_use_ability",
                    "payload": {"unitId": scout_id, "abilityTypeId": 1}
                }))
                print("SENSOR_SWEEP_SENT", flush=True)
                # Then move toward Mars
                wsa.send(json.dumps({
                    "type": "mmo_move_unit",
                    "payload": {"unitId": scout_id, "targetHex": target}
                }))
                print("MOVE_SENT", flush=True)

            elif t == "mmo_world_state":
                chunks = p.get("chunks", [])
                all_units  = [u for c in chunks for u in c.get("units", [])]
                all_astro  = [a for c in chunks for a in c.get("asteroids", [])]
                our_units  = [u for u in all_units if u.get("ownerId") == d["commander"]["userId"]]
                edf_units  = [u for u in all_units if u.get("ownerName") == "Earth Defense Force"]

                results['units']    = our_units
                results['edf']      = edf_units
                results['asteroids'] = all_astro

                print(f"WORLD: {len(all_units)} units, {len(all_astro)} asteroids, {len(edf_units)} EDF", flush=True)
                for u in our_units:
                    pos = u.get('position',{})
                    print(f"  OUR {u['type']} at ({pos.get('q')},{pos.get('r')}) HP={u.get('currentHp')}", flush=True)
                for e in edf_units[:5]:
                    print(f"  EDF {e['type']} at ({e['position']['q']},{e['position']['r']}) HP={e.get('currentHp')}", flush=True)
                for a in all_astro[:10]:
                    print(f"  Ast id={a.get('id')} variant={a.get('variant')} minerals={a.get('mineralComposition')}", flush=True)
                got_world[0] = True
                wsa.close()

            elif t == "mmo_move_unit":
                print(f"MOVE_RESULT: {json.dumps(p)}", flush=True)
                results['move'] = p
                moved[0] = True

            elif t == "mmo_use_ability":
                print(f"ABILITY_RESULT: {json.dumps(p)}", flush=True)
                results['ability'] = p
                swept[0] = True

            elif t == "error":
                print(f"ERROR: {json.dumps(p)}", flush=True)
                results['error'] = p

        except Exception as e:
            print(f"ERR: {e}", flush=True)

    ws_app = websocket.WebSocketApp(
        'wss://crimsonmandate.com/ws',
        on_open=on_open,
        on_message=on_msg
    )
    ws_app.run_forever(ping_interval=10, ping_timeout=8)
    return results

if __name__ == "__main__":
    import time, signal, threading

    def timeout_handler():
        print("TIMEOUT", flush=True)
        sys.exit(0)

    t = threading.Timer(20, timeout_handler)
    t.start()

    r = run()
    t.cancel()

    print("=== FINAL RESULTS ===")
    print(json.dumps(r, indent=2, default=str))
