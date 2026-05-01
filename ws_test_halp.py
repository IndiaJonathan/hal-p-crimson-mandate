#!/usr/bin/env python3
import json, websocket, time, sys
sys.path.insert(0, "/Users/jonathan/.openclaw/workspace/crimson-mandate-agent")
with open("/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/state.json") as f:
    state = json.load(f)
token = state["session"]["token"]
SCOUT_ID = "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_respawn_f696459e"

def on_msg(ws, msg):
    try:
        data = json.loads(msg)
        t = data.get("type", "")
        p = data.get("payload", {})
        if t == "mmo_world_state":
            chunks = p.get("chunks", [])
            asteroids = [a for c in chunks for a in c.get("asteroids", [])]
            units_all = [u for c in chunks for u in c.get("units", [])]
            edf = [u for u in units_all if u.get("ownerName") == "Earth Defense Force"]
            our = [u for u in units_all if u.get("ownerId") and "0a8a2ff5" in u.get("ownerId", "")]
            print("WORLD: %d units, %d asteroids, %d EDF" % (len(units_all), len(asteroids), len(edf)))
            for a in asteroids[:5]:
                print("  Ast: %s at %s min=%s" % (a.get("variant"), a.get("position"), a.get("mineralComposition")))
            for e in edf[:3]:
                print("  EDF: %s at %s HP=%s" % (e["type"], e.get("position"), e.get("currentHp")))
            for u in our:
                print("  OUR: %s at %s HP=%s" % (u["type"], u.get("position"), u.get("currentHp")))
        elif t == "mmo_unit_moved":
            print("MOVED: %s" % p.get("position"))
        elif t == "mmo_golden_asteroid_spawned":
            print("GOLDEN: %s" % p.get("position"))
        elif t == "mmo_resources":
            print("ISD: %s | Cr: %s" % (p.get("isdBalance"), p.get("credits")))
        elif t not in ("mmo_tick", "mmo_pong"):
            print("MSG: %s" % t)
    except Exception as e:
        print("ERR: %s" % e)

def on_open(ws):
    ws.send(json.dumps({"type": "auth", "token": token}))
    time.sleep(0.5)
    ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
    time.sleep(2)
    ws.send(json.dumps({"type": "mmo_move_unit", "payload": {"unitId": SCOUT_ID, "targetHex": {"q": 3, "r": -1}}}))
    print("Move sent to (3,-1)")

ws = websocket.WebSocketApp("wss://crimsonmandate.com/ws", on_message=on_msg)
ws.on_open = on_open
ws.run_forever(ping_interval=15, ping_timeout=10)
