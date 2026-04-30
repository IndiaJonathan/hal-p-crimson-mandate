#!/usr/bin/env python3
"""WS connect + move + check results"""
import json, time, sys
sys.path.insert(0, '/Users/jonathan/.openclaw/workspace/crimson-mandate-agent')

try:
    import websocket
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client"])
    import websocket

with open('/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/state.json') as f:
    state = json.load(f)
token = state["session"]["token"]

ws_url = "wss://crimsonmandate.com/ws"

# Next move: (4,-2)
next_x, next_y = 4, -2
scout_id = "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_respawn_f696459e"

move_done = [False]
move_result = [None]

def on_message(ws, msg):
    try:
        data = json.loads(msg)
        t = data.get("type", "")
        p = data.get("payload", {})

        if t == "auth_success":
            print("✓ auth")
        elif t == "mmo_world_state":
            chunks = p.get("chunks", [])
            total_a = sum(len(c.get("asteroids",[])) for c in chunks)
            total_e = sum(len(c.get("enemies",[])) for c in chunks)
            print(f"WorldState: {len(chunks)} chunks, {total_a} asteroids, {total_e} EDF")
            units = [u for c in chunks for u in c.get("units",[])]
            for u in units:
                if "respawn" in u.get("id",""):
                    print(f"  Scout at ({u.get('x')},{u.get('y')})")
        elif t == "mmo_unit_moved":
            print(f"MOVED → ({p.get('x')},{p.get('y')}) id={p.get('unitId','')[:30]}")
            move_done[0] = True
            move_result[0] = p
        elif t == "mmo_error":
            print(f"ERROR: {p}")
            move_result[0] = {"error": p}
        elif t == "mmo_golden_asteroid_spawned":
            print(f"🌟 GOLDEN at {p.get('position')} id={p.get('id')}")
        else:
            pass  # reduce noise
    except: pass

def on_open(ws):
    ws.send(json.dumps({"type": "auth", "token": token}))
    time.sleep(0.4)
    ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
    time.sleep(0.6)
    ws.send(json.dumps({
        "type": "mmo_unit_move",
        "payload": {"unitId": scout_id, "x": next_x, "y": next_y}
    }))
    time.sleep(1.5)
    ws.send(json.dumps({"type": "mmo_world_state_request", "payload": {"worldId": 1}}))
    time.sleep(2)
    ws.close()

ws = websocket.WebSocketApp(ws_url, on_message=on_message)
ws.on_open = on_open

import threading
t = threading.Thread(target=lambda: ws.run_forever(ping_interval=15, ping_timeout=10))
t.daemon = True
t.start()
t.join(timeout=20)

print(f"\nMove done: {move_done[0]}")
print(f"Result: {move_result[0]}")