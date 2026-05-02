#!/usr/bin/env python3
"""Test WebSocket for component sell / trade functionality"""
import json, websocket, time, sys

with open("state.json") as f:
    state = json.load(f)
token = state["session"]["token"]

results = []

def on_open(ws):
    ws.send(json.dumps({"type": "auth", "token": token}))
    time.sleep(0.5)
    ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))

def on_msg(ws, msg):
    try:
        data = json.loads(msg)
        t = data.get("type", "")
        p = data.get("payload", {})
        results.append({"type": t, "payload": p})
        if t == "mmo_world_joined":
            # Try mmo_sell_component
            ws.send(json.dumps({
                "type": "mmo_sell_component",
                "payload": {
                    "componentName": "wpn_beam_laser_light",
                    "quantity": 1
                }
            }))
            print("mmo_sell_component sent")
            time.sleep(1)
            # Try mmo_sell_item
            ws.send(json.dumps({
                "type": "mmo_sell_item",
                "payload": {
                    "itemId": "wpn_beam_laser_light",
                    "quantity": 1
                }
            }))
            print("mmo_sell_item sent")
            time.sleep(1)
            # Try mmo_trade
            ws.send(json.dumps({
                "type": "mmo_trade",
                "payload": {
                    "action": "sell",
                    "componentName": "wpn_beam_laser_light",
                    "quantity": 1
                }
            }))
            print("mmo_trade sent")
            time.sleep(2)
            ws.close()
    except Exception as e:
        print(f"Err: {e}")

ws = websocket.WebSocketApp(
    "wss://crimsonmandate.com/ws",
    on_open=on_open,
    on_message=on_msg
)
print("Connecting to WS...")
ws.run_forever(ping_interval=10, ping_timeout=5)

print("\n=== All message types received ===")
msg_types = set(r.get("type") for r in results)
for t in sorted(msg_types):
    count = sum(1 for r in results if r.get("type") == t)
    print(f"  {t}: {count} occurrences")

# Also show any error messages
errors = [r for r in results if r.get("type") == "error"]
if errors:
    print("\n=== Errors ===")
    for e in errors[:5]:
        print(f"  {e}")