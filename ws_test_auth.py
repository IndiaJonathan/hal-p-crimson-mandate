#!/usr/bin/env python3
"""Test WS join world + unit move"""
import json, time, sys
sys.path.insert(0, '/Users/jonathan/.openclaw/workspace/crimson-mandate-agent')

try:
    import websocket as ws_module
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client"])
    import websocket as ws_module

with open('/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/state.json') as f:
    state = json.load(f)
token = state["session"]["token"]
session_id = state["session"]["sessionId"]

ws_url = "wss://crimsonmandate.com/ws"

all_msgs = []
move_done = [False]
move_result = [None]
world_state_received = [False]

def on_message(ws, msg):
    all_msgs.append(msg)
    try:
        data = json.loads(msg)
        t = data.get("type", "")
        p = data.get("payload", {})
        print(f"[{t}] {json.dumps(p)[:150]}")
        if t == "mmo_unit_moved":
            move_done[0] = True
            move_result[0] = p
        if t == "mmo_world_state":
            world_state_received[0] = True
    except:
        print(f"Raw: {msg[:100]}")

def on_open(ws):
    print("=== OPEN ===")
    # Try auth with sessionId too
    ws.send(json.dumps({"type": "auth", "token": token, "sessionId": session_id}))
    time.sleep(0.5)
    # Try join world
    ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
    time.sleep(1)
    # Try move
    scout_id = "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_respawn_f696459e"
    ws.send(json.dumps({
        "type": "mmo_unit_move",
        "payload": {"unitId": scout_id, "x": 4, "y": -2}
    }))
    time.sleep(2)
    ws.send(json.dumps({"type": "mmo_world_state_request", "payload": {"worldId": 1}}))
    time.sleep(2)
    ws.close()

def on_error(ws, err):
    print(f"ERROR: {err}")

def on_close(ws, *args):
    print(f"Closed")

ws = ws_module.WebSocketApp(ws_url,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close)
ws.on_open = on_open

import threading
t = threading.Thread(target=lambda: ws.run_forever(ping_interval=10))
t.daemon = True
t.start()
t.join(timeout=15)

print(f"\n=== FINAL ===")
print(f"Move done: {move_done[0]}")
print(f"World state received: {world_state_received[0]}")
print(f"Move result: {move_result[0]}")
print(f"Total msgs: {len(all_msgs)}")