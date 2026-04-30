#!/usr/bin/env python3
"""
HALP Scout mover via WebSocket — toward Mars (12,-5)
Scout at (2,0), moves one step: (3,-1), then (4,-2), etc.
"""
import json, time, sys
sys.path.insert(0, '/Users/jonathan/.openclaw/workspace/crimson-mandate-agent')

try:
    import websocket
except ImportError:
    print("Installing websocket-client...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client"])
    import websocket

with open('/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/state.json') as f:
    state = json.load(f)
token = state["session"]["token"]

# Scout position tracking (hardcoded from last known)
# HALP scout at (2,0), last move was to (3,-1)
# Next step toward Mars: (4,-2)
current_x, current_y = 3, -1  # last confirmed
next_x, next_y = current_x + 1, current_y - 1  # = (4,-2)
target_x, target_y = 12, -5  # Mars

print(f"=== HALP Scout Move (WS) ===")
print(f"Current: ({current_x},{current_y})")
print(f"Next: ({next_x},{next_y})")
print(f"Mars target: ({target_x},{target_y})")

ws_url = "wss://crimsonmandate.com/ws"
result = {}

def on_message(ws, msg):
    global result
    try:
        data = json.loads(msg)
        t = data.get("type", "")
        payload = data.get("payload", {})

        if t == "auth_success":
            print("✓ WS auth success")
        elif t == "mmo_world_state":
            chunks = payload.get("chunks", [])
            print(f"\nWorld state received — {len(chunks)} chunks")
            total_asteroids = sum(len(c.get("asteroids", [])) for c in chunks)
            total_enemies = sum(len(c.get("enemies", [])) for c in chunks)
            print(f"  Asteroids: {total_asteroids}")
            print(f"  EDF fighters: {total_enemies}")
            result["asteroids"] = total_asteroids
            result["edf"] = total_enemies

            # Show scout positions
            all_units = [u for c in chunks for u in c.get("units", [])]
            print(f"  Total units visible: {len(all_units)}")
            for u in all_units:
                oid = u.get("ownerId", "?")
                name = u.get("name", "?")
                ux, uy = u.get("x", 0), u.get("y", 0)
                print(f"    Unit {name} at ({ux},{uy}) owner={oid}")
                result["scout_x"] = ux
                result["scout_y"] = uy
        elif t == "mmo_unit_moved":
            new_x = payload.get("x")
            new_y = payload.get("y")
            unit_id = payload.get("unitId", "?")
            print(f"\n✓ Unit moved: {unit_id} → ({new_x},{new_y})")
            result["moved_to"] = f"({new_x},{new_y})"
            result["move_success"] = True
        elif t == "mmo_error":
            print(f"\n✗ WS error: {payload}")
            result["error"] = payload
        else:
            print(f"  [{t}] {json.dumps(payload)[:120]}")
    except Exception as e:
        print(f"msg parse error: {e} | {msg[:100]}")

def on_error(ws, err):
    print(f"WS ERROR: {err}")

def on_close(ws, *args):
    print("WS closed")

def on_open(ws):
    # Auth
    ws.send(json.dumps({"type": "auth", "token": token}))
    time.sleep(0.3)
    # Join world
    ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
    time.sleep(0.5)
    # Move HALP scout toward Mars
    # Use the respawned scout ID
    scout_id = "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_respawn_f696459e"
    move_cmd = {
        "type": "mmo_unit_move",
        "payload": {
            "unitId": scout_id,
            "x": next_x,
            "y": next_y
        }
    }
    print(f"\nSending move: {json.dumps(move_cmd)}")
    ws.send(json.dumps(move_cmd))
    time.sleep(1)
    # Request world state to see results
    ws.send(json.dumps({"type": "mmo_world_state_request", "payload": {"worldId": 1}}))
    time.sleep(1)
    ws.close()

ws = websocket.WebSocketApp(ws_url,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close)
ws.on_open = on_open
ws.run_forever(ping_interval=20, ping_timeout=10)

print("\n=== RESULT ===")
print(json.dumps(result, indent=2))