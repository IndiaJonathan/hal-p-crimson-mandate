#!/usr/bin/env python3
"""
Crimson Mandate — Persistent Golden Asteroid Hunter
Keeps a dedicated WebSocket connection open 24/7.
When a golden asteroid spawns, moves to it and claims it.
Notifies HAL-P main session on Discord after each claim.
"""
import json, os, sys, time, logging, threading

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(AGENT_DIR, "golden_hunter.log")
STATE_FILE = os.path.join(AGENT_DIR, "state.json")

# ─── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] golden-hunter: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("golden-hunter")

# ─── Distance (axial hex, same as decisions.py) ────────────────────────────

def distance_hex(a, b):
    q1, r1 = a.get("q", 0), a.get("r", 0)
    q2, r2 = b.get("q", 0), b.get("r", 0)
    return max(abs(q1 - q2), abs(r1 - r2), abs((q1 + r1) - (q2 + r2)))

# ─── Scout config ────────────────────────────────────────────────────────────

SCOUT_ID   = "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_1"
SCOUT_OWNER = "0a8a2ff5-1b93-44c3-994c-6891e0076d72"

# ─── WebSocket client (standalone, no class-level shared state) ───────────────

WS_URL = "wss://crimsonmandate.com/ws"

class HunterClient:
    def __init__(self, token: str, session_id: str):
        self.token   = token
        self.session_id = session_id
        self.running = False
        self.ws      = None
        self.thread  = None
        self._events  = {}
        self._cv      = threading.Condition()
        self._die     = threading.Event()
        self._auth_ok = threading.Event()

    def start(self):
        import websocket
        self.running = True
        self.thread  = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        import websocket
        while self.running and not self._die.is_set():
            try:
                self.ws = websocket.WebSocketApp(
                    WS_URL,
                    on_open    = self._on_open,
                    on_message = self._on_message,
                    on_error   = lambda ws, e: None,
                    on_close   = lambda ws, *a: None,
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception:
                pass
            if self.running and not self._die.is_set():
                time.sleep(2)

    def _on_open(self, ws):
        self._send({"type": "auth", "payload": {"sessionId": self.token}})

    def _on_message(self, ws, msg):
        try:
            data = json.loads(msg)
        except:
            return
        msg_type = data.get("type", "unknown")
        payload  = data.get("payload", data)

        with self._cv:
            self._events.setdefault(msg_type, []).append(payload)
            self._cv.notify_all()

        if msg_type == "auth_success":
            self._auth_ok.set()
            self._send({"type": "mmo_join_world", "payload": {"worldId": 1}})

        elif msg_type == "mmo_world_joined":
            log.info("World joined — ready to hunt")

    def _send(self, msg):
        if self.ws and self.running:
            try:
                self.ws.send(json.dumps(msg))
            except Exception as e:
                log.warning(f"Send error: {e}")

    def wait_for(self, msg_type: str, timeout: float = 12.0):
        with self._cv:
            end = time.time() + timeout
            while time.time() < end:
                if self._events.get(msg_type):
                    return self._events.pop(msg_type)
                remaining = end - time.time()
                if remaining <= 0:
                    break
                self._cv.wait(timeout=min(remaining, 1.0))
            return self._events.pop(msg_type, [])

    def wait_for_auth(self, timeout: float = 10.0) -> bool:
        started = time.time()
        while time.time() - started < timeout:
            if self._auth_ok.is_set():
                return True
            time.sleep(0.2)
        return False

    def get_scout_position(self) -> dict:
        """Fetch current scout position from world state."""
        msgs = self.wait_for("mmo_world_state", timeout=15)
        if not msgs:
            return {}
        state = msgs[-1]
        for unit in state.get("units", []):
            if unit.get("id") == SCOUT_ID:
                return unit.get("position", {})
        return {}

    def stop(self):
        self.running = False
        self._die.set()
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        if self.thread:
            self.thread.join(timeout=3)


# ─── Notification via Discord sessions_send ────────────────────────────────

def notify_hal_p(message: str):
    """Ping the main agent session on Discord."""
    try:
        import requests
        # sessions_send is a tool — we call it via the agent's own tooling.
        # Since we're a subagent we can just print and let parent handle it.
        # For persistent-launchd context, write to a flag file the main session reads.
        flag_file = os.path.join(AGENT_DIR, "..", "..", "reports", "golden-hunter-claim.flag")
        with open(flag_file, "w") as f:
            f.write(message + "\n")
        log.info(f"Notified HAL-P: {message}")
    except Exception as e:
        log.error(f"Failed to notify HAL-P: {e}")


# ─── Main hunt loop ──────────────────────────────────────────────────────────

def hunt_cycle():
    """Run one persistent connection + hunt cycle. Returns True if claimed."""
    state = load_state()
    token     = state.get("session", {}).get("token", "")
    session_id = state.get("session", {}).get("sessionId", "")

    if not token or not session_id:
        log.error("No session token — run auth.py first")
        return False

    log.info(f"Connecting (scout={SCOUT_ID})...")
    client = HunterClient(token, session_id)
    client.start()

    if not client.wait_for_auth(timeout=12):
        log.error("Auth timeout — reconnecting")
        client.stop()
        return False

    log.info("Authenticated — waiting for golden asteroid spawn...")

    # Wait up to 5 minutes for a golden asteroid
    timeout = 300
    golden  = None
    end     = time.time() + timeout
    while time.time() < end:
        with client._cv:
            remaining = end - time.time()
            if remaining <= 0:
                break
            client._cv.wait(timeout=min(remaining, 10.0))
        # Check via the condition notified on golden asteroid
        with client._cv:
            for ev in client._events.get("mmo_golden_asteroid_spawned", []):
                golden = ev
                client._events["mmo_golden_asteroid_spawned"] = []
                break
        if golden:
            break

    if not golden:
        log.info(f"No golden asteroid in {timeout}s — reconnecting loop")
        client.stop()
        return False

    log.warning(f"🌟 GOLDEN ASTEROID SPAWNED: {golden}")

    gpos    = golden.get("position", {})
    gpos_q, gpos_r = gpos.get("q", 0), gpos.get("r", 0)
    log.info(f"Position: q={gpos_q} r={gpos_r}")

    # Get current scout position
    scout_pos = client.get_scout_position()
    if not scout_pos:
        log.warning("Could not get scout position — attempting to proceed anyway")

    # ── Move toward asteroid if needed ─────────────────────────────────────────
    scout_q = scout_pos.get("q", 0)
    scout_r = scout_pos.get("r", 0)
    dist    = distance_hex(scout_pos, gpos)
    log.info(f"Scout at ({scout_q},{scout_r}) → asteroid at ({gpos_q},{gpos_r}) | dist={dist}")

    if dist > 1:
        # Move one step toward target
        q_diff = gpos_q - scout_q
        r_diff = gpos_r - scout_r
        step_q = 0 if q_diff == 0 else (1 if q_diff > 0 else -1)
        step_r = 0 if r_diff == 0 else (1 if r_diff > 0 else -1)
        move_target = {"q": scout_q + step_q, "r": scout_r + step_r}

        log.info(f"Moving scout to ({move_target['q']},{move_target['r']})")
        client._send({
            "type": "mmo_move_unit",
            "payload": {"unitId": SCOUT_ID, "targetHex": move_target}
        })
        moved = client.wait_for("mmo_unit_moved", timeout=15)
        if moved:
            log.info("Scout moved one step")
        else:
            log.warning("Move confirmation not received — proceeding anyway")

    # ── Claim ──────────────────────────────────────────────────────────────────
    log.info(f"Claiming golden asteroid {golden.get('id')}")
    client._send({
        "type": "mmo_claim_golden_asteroid",
        "payload": {"asteroidId": golden.get("id")}
    })

    result = client.wait_for("mmo_golden_asteroid_claimed", timeout=20)
    if result:
        log.warning(f"🌟 CLAIMED! Result: {result}")
        notify_hal_p(f"Golden asteroid claimed! Details: {result}")
    else:
        log.error("Claim timed out — may not have succeeded")

    client.stop()
    return True


# ─── State helper (mirror runner.py) ────────────────────────────────────────

def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {}


# ─── Persistent driver ──────────────────────────────────────────────────────

def main():
    log.info("═══════════════════════════════════════")
    log.info("Golden Asteroid Hunter — STARTING (24/7)")
    log.info("═══════════════════════════════════════")

    cycle = 0
    while True:
        cycle += 1
        log.info(f"--- Cycle {cycle} ---")
        try:
            claimed = hunt_cycle()
            if claimed:
                log.info("Claim complete — back to hunting")
            # Brief pause between cycles to avoid hammering on reconnect
            time.sleep(2)
        except Exception as e:
            log.error(f"Hunt cycle error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()