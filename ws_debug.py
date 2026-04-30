#!/usr/bin/env python3
"""Debug WS connection with verbose logging"""
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

print(f"Token starts with: {token[:30]}")
print(f"Connecting to wss://crimsonmandate.com/ws ...")

# Try standard WebSocket connection
import socket

# First test: basic TCP connect to crimsonmandate.com:443
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10)
try:
    sock.connect(("crimsonmandate.com", 443))
    print("✓ TCP connected to crimsonmandate.com:443")
    sock.close()
except Exception as e:
    print(f"✗ TCP failed: {e}")

# Try ws connection
ws_url = "wss://crimsonmandate.com/ws"
msgs = []
connected = [False]
authed = [False]

def on_message(ws, msg):
    msgs.append(msg)
    print(f"MSG [{msg[:80]}]")
    data = json.loads(msg) if msg.startswith('{') else {}
    if data.get("type") == "auth_success":
        authed[0] = True
        print("✓ Auth success")

def on_open(ws):
    connected[0] = True
    print("WS opened, sending auth...")
    ws.send(json.dumps({"type": "auth", "token": token}))

def on_error(ws, err):
    print(f"WS error: {err}")

def on_close(ws, *args):
    print(f"WS closed: args={args}")

ws = ws_module.WebSocketApp(ws_url,
    on_message=on_message,
    on_open=on_open,
    on_error=on_error,
    on_close=on_close)

import threading
t = threading.Thread(target=lambda: ws.run_forever(ping_interval=10))
t.daemon = True
t.start()
time.sleep(5)
print(f"\nConnected: {connected[0]}, Authed: {authed[0]}, Msgs: {len(msgs)}")
print(f"All msgs: {msgs}")