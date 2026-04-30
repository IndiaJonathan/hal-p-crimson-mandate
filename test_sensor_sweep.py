#!/usr/bin/env python3
"""Test sensor sweep ability — boosts sensor range by 3 hexes for 10 ticks"""
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

scout_id = "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_respawn_f696459e"
results = {"world_state": None, "sensor_result": None, "moved": False}

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
            results["world_state"] = {"chunks": len(chunks), "asteroids": total_a, "edf": total_e}
            # Also print golden asteroid info if any
            for c in chunks:
                for a in c.get("asteroids", []):
                    if a.get("variant") == "golden":
                        print(f"  🌟 GOLDEN ASTEROID in chunk: {a.get('position')}")
        elif t == "mmo_unit_moved":
            print(f"MOVED → ({p.get('x')},{p.get('y')})")
            results["moved"] = True
        elif t == "mmo_error":
            print(f"ERROR: {p}")
        elif t == "mmo_golden_asteroid_spawned":
            print(f"🌟 GOLDEN SPAWNED at {p.get('position')}")
        elif t == "mmo_sensor_sweep_result":
            print(f"📡 SENSOR SWEEP RESULT: {p}")
            results["sensor_result"] = p
        elif t == "mmo_ability_result":
            print(f"⚡ ABILITY: {p}")
        else:
            # Print any message with "sweep" or "sensor" in it
            msg_str = str(data)
            if "sweep" in msg_str.lower() or "sensor" in msg_str.lower():
                print(f"  [sensor-related] {data}")
    except Exception as e:
        print(f"parse error: {e}")

def on_open(ws):
    ws.send(json.dumps({"type": "auth", "token": token}))
    time.sleep(0.5)
    ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
    time.sleep(0.8)
    # Fire sensor sweep
    ws.send(json.dumps({
        "type": "mmo_use_ability",
        "payload": {"unitId": scout_id, "abilityTypeId": 1}
    }))
    print(f"⚡ Sensor Sweep fired on {scout_id}")
    time.sleep(3)
    # Request world state
    ws.send(json.dumps({"type": "mmo_world_state_request", "payload": {"worldId": 1}}))
    time.sleep(3)
    ws.close()

ws = websocket.WebSocketApp(ws_url, on_message=on_message)
ws.on_open = on_open

import threading
t = threading.Thread(target=lambda: ws.run_forever(ping_interval=15, ping_timeout=10))
t.daemon = True
t.start()
t.join(timeout=20)

print(f"\nResults: {json.dumps(results, indent=2)}")
