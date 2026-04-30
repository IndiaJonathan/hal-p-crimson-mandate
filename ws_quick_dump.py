#!/usr/bin/env python3
"""Quick WS world state dump — see what's actually visible"""
import json, time, websocket, sys

with open('/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/state.json') as f:
    state = json.load(f)
token = state["session"]["token"]

ws_url = "wss://crimsonmandate.com/ws"
done = False

def on_message(ws, msg):
    global done
    try:
        data = json.loads(msg)
        t = data.get("type", "")
        p = data.get("payload", {})

        if t == "connected":
            ws.send(json.dumps({"type": "auth", "token": token}))
        elif t == "auth_success":
            ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
        elif t == "mmo_world_joined":
            time.sleep(0.5)
            ws.send(json.dumps({"type": "mmo_world_state_request", "payload": {"worldId": 1}}))
        elif t == "mmo_world_state":
            chunks = p.get("chunks", [])
            print(f"Chunks: {len(chunks)}")
            for i, c in enumerate(chunks):
                cx = c.get("x", "?")
                cy = c.get("y", "?")
                asteroids = c.get("asteroids", [])
                enemies = c.get("enemies", [])
                units = c.get("units", [])
                print(f"  Chunk ({cx},{cy}): {len(asteroids)} ast, {len(enemies)} edf, {len(units)} units")
                for u in units:
                    print(f"    Unit: name={u.get('name','?')} id={u.get('id','')[:50]} "
                          f"at=({u.get('x',0)},{u.get('y',0)}) owner={u.get('ownerId','?')}")
            done = True
            ws.close()
    except Exception as e:
        print(f"err: {e}")

ws = websocket.WebSocketApp(ws_url, on_message=on_message)
ws.run_forever(ping_interval=15)
print("Done")