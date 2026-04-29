#!/usr/bin/env python3
"""
Multi-Account Golden Asteroid Hunter for Crimson Mandate.
Runs 2 accounts simultaneously — first one to reach a golden asteroid claims it.
"""
import json, time, threading, sys, urllib.request
from pathlib import Path

BASE_URL = "https://crimsonmandate.com"
LOG_FILE = "/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/golden_hunter_multi.log"
FLAG_FILE = "/tmp/golden-claimed-flag.txt"

ACCOUNTS = [
    {"email": "halp@burk-dashboards.com", "password": "Test1234!", "account_name": "halp-main"},
    {"email": "halp2@burk-dashboards.com", "password": "Test1234!", "account_name": "halp2"},
]

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    Path(LOG_FILE).open("a").write(line + "\n")

def login(email, password):
    import requests
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=15
    )
    data = resp.json()
    if not data.get("success"):
        log(f"[{email}] Login failed: {data}")
        return None
    return data["data"]

def distance_hex(pos1, pos2):
    def cube(q, r):
        x, z = q, r
        y = -x - z
        return (x, y, z)
    c1 = cube(pos1.get("q", 0), pos1.get("r", 0))
    c2 = cube(pos2.get("q", 0), pos2.get("r", 0))
    return max(abs(c1[i] - c2[i]) for i in range(3))

def message_halp(text):
    """Message HAL-P main session via Discord."""
    try:
        req = urllib.request.Request(
            "http://localhost:18789/api/sessions",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            sessions = json.loads(resp.read())
        session_key = None
        for s in sessions:
            if s.get("kind") == "main":
                session_key = s.get("sessionKey") or s.get("key")
                break
        if not session_key:
            log("[HAL-P] No main session found")
            return
        data = json.dumps({"content": text}).encode()
        req = urllib.request.Request(
            f"http://localhost:18789/api/sessions/{session_key}/messages",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            log(f"[HAL-P] Discord message sent")
    except Exception as e:
        log(f"[HAL-P] Message error: {e}")


class GoldenHunter:
    def __init__(self, email, password, account_name):
        self.email = email
        self.account_name = account_name
        self.token = None
        self.session_id = None
        self.running = True
        self.ws = None
        self.golden_payload = None
        self.golden_pos = None
        self.lock = threading.Lock()
        self.scout_pos = {"q": 0, "r": 0}

        result = login(email, password)
        if result:
            self.token = result["token"]
            self.session_id = result["sessionId"]
            log(f"[{email}] Authenticated — token OK")
        else:
            self.running = False

    def run(self):
        import websocket
        ws_url = "wss://crimsonmandate.com/ws"

        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                log(f"[{self.email}] Connecting WS...")
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                log(f"[{self.email}] WS error: {e}")
            if self.running:
                time.sleep(3)

    def _on_open(self, ws):
        ws.send(json.dumps({"type": "auth", "token": self.token}))
        ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
        log(f"[{self.email}] WS opened — joined world")

    def _on_message(self, ws, msg):
        try:
            data = json.loads(msg)
            msg_type = data.get("type", "")
            payload = data.get("payload", {})

            if msg_type == "auth_success":
                log(f"[{self.email}] WS auth success")
            elif msg_type == "mmo_world_state":
                # Extract own scout position
                try:
                    chunks = payload.get("chunks", [])
                    units = [u for c in chunks for u in c.get("units", [])]
                    for u in units:
                        if u.get("ownerId") and u["ownerId"] != "Unknown":
                            # Try to find our scout by checking all units
                            pass
                except: pass
            elif msg_type == "mmo_golden_asteroid_spawned":
                self.golden_payload = payload
                self.golden_pos = payload.get("position", {})
                log(f"[{self.email}] 🌟 Golden asteroid at {self.golden_pos}")
                # Race to claim it
                self._race_claim()
            elif msg_type == "mmo_golden_asteroid_claimed":
                amt = payload.get("cryptoRewarded", 0)
                claimer = payload.get("claimerId", "?")
                log(f"[{self.email}] ✅ Golden asteroid claimed! ISD earned: {amt} by {claimer}")
                if amt > 0:
                    msg = f"🌟 Golden asteroid claimed! ~{amt} ISD earned on {self.account_name}!"
                    message_halp(msg)
                    Path(FLAG_FILE).write_text(f"{time.time()}|{amt}|{self.account_name}")
            elif msg_type == "mmo_resources":
                pass  # balance updates handled elsewhere
        except Exception as e:
            log(f"[{self.email}] msg error: {e}")

    def _on_error(self, ws, error):
        log(f"[{self.email}] WS error: {error}")

    def _on_close(self, ws, *args):
        log(f"[{self.email}] WS closed")

    def _send(self, msg):
        if self.ws:
            try:
                self.ws.send(json.dumps(msg))
            except:
                pass

    def _race_claim(self):
        """Race to claim the golden asteroid."""
        if not self.golden_payload:
            return
        asteroid_id = self.golden_payload.get("id")
        if not asteroid_id:
            return
        # Brief delay so all hunters can attempt simultaneously
        time.sleep(0.5)
        self._send({
            "type": "mmo_claim_golden_asteroid",
            "payload": {"asteroidId": asteroid_id}
        })
        log(f"[{self.email}] Claim sent for {asteroid_id}")

    def stop(self):
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except:
                pass


def main():
    log("=" * 60)
    log("Multi-Account Golden Asteroid Hunter — STARTING")
    log("=" * 60)

    hunters = []
    threads = []

    for acct in ACCOUNTS:
        hunter = GoldenHunter(acct["email"], acct["password"], acct["account_name"])
        if hunter.token:
            hunters.append(hunter)
            t = threading.Thread(target=hunter.run, daemon=True)
            t.start()
            threads.append(t)
            log(f"[{acct['email']}] Hunter thread started")
            time.sleep(1)  # stagger connections slightly

    log(f"=== {len(hunters)} hunters running ===")

    try:
        while True:
            time.sleep(30)
            alive = [h.email for h in hunters if h.running]
            log(f"Heartbeat — alive: {len(alive)}/{len(hunters)}")
    except KeyboardInterrupt:
        log("CTRL+C — stopping all hunters")
        for h in hunters:
            h.stop()

if __name__ == "__main__":
    main()
