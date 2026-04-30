#!/usr/bin/env python3
"""HALP Scout mover via WebSocket — robust version"""
import json, time, sys
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
scout_id = None
scout_pos = (3, -1)  # last confirmed
move_result = None

def on_message(ws, msg):
    global scout_id, scout_pos, move_result
    try:
        data = json.loads(msg)
        t = data.get("type", "")
        p = data.get("payload", {})

        if t == "connected":
            print(f"✓ Connected (clientId: {p.get('clientId', '?')[:20]})")
            ws.send(json.dumps({"type": "auth", "token": token}))

        elif t == "auth_success":
            print("✓ Authenticated")
            time.sleep(0.5)
            ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))

        elif t == "mmo_world_joined":
            print(f"✓ World joined: {p}")
            time.sleep(0.5)
            ws.send(json.dumps({"type": "mmo_world_state_request", "payload": {"worldId": 1}}))

        elif t == "mmo_world_state":
            chunks = p.get("chunks", [])
            units = [u for c in chunks for u in c.get("units", [])]
            total_asteroids = sum(len(c.get("asteroids", [])) for c in chunks)
            total_edf = sum(len(c.get("enemies", [])) for c in chunks)
            print(f"World state: {len(chunks)} chunks, {len(units)} units, "
                  f"{total_asteroids} asteroids, {total_edf} EDF")

            for u in units:
                uid = u.get("id", "")
                name = u.get("name", "?")
                x, y = u.get("x", 0), u.get("y", 0)
                oid = u.get("ownerId", "?")
                # Check if it's HALP's scout
                if "halp" in name.lower() or "respawn_f696459e" in uid:
                    scout_id = uid
                    scout_pos = (x, y)
                    print(f"  HALP Scout: id={uid[:50]} at ({x},{y}) owner={oid}")

            if scout_id is None:
                # Try to find by checking all scouts
                for u in units:
                    if "scout" in u.get("name", "").lower():
                        print(f"  Scout candidate: id={u.get('id','')[:50]} "
                              f"at ({u.get('x',0)},{u.get('y',0)}) owner={u.get('ownerId','?')}")

            if scout_id:
                # Execute move toward Mars: (12,-5)
                next_x, next_y = scout_pos[0] + 1, scout_pos[1] - 1
                print(f"\nMoving scout from {scout_pos} → ({next_x},{next_y})")
                ws.send(json.dumps({
                    "type": "mmo_unit_move",
                    "payload": {"unitId": scout_id, "x": next_x, "y": next_y}
                }))
                time.sleep(1)
                ws.send(json.dumps({"type": "mmo_world_state_request", "payload": {"worldId": 1}}))
            else:
                print("No HALP scout found in world state!")
                time.sleep(1)
                ws.close()

        elif t == "mmo_unit_moved":
            nx, ny = p.get("x"), p.get("y")
            print(f"✓ Scout moved to ({nx},{ny})")
            move_result = {"moved_to": f"({nx},{ny})", "success": True}
            scout_pos = (nx, ny)
            time.sleep(1)
            ws.close()

        elif t == "mmo_error":
            print(f"✗ Error: {p}")
            move_result = {"error": str(p)}

        else:
            print(f"  [{t}] {str(p)[:100]}")
    except Exception as e:
        print(f"Parse error: {e} | {msg[:100]}")

def on_error(ws, err):
    print(f"WS ERROR: {err}")

def on_close(ws, *args):
    print("WS closed")

ws = websocket.WebSocketApp(ws_url,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close)

def run():
    ws.run_forever(ping_interval=20, ping_timeout=10)

import threading
t = threading.Thread(target=run, daemon=True)
t.start()
t.join(timeout=25)

print(f"\n=== RESULT ===")
print(f"Scout position: {scout_pos}")
print(f"Move result: {json.dumps(move_result)}")
print(f"Scout ID: {scout_id}")