#!/usr/bin/env python3
"""
Crimson Mandate Agent — Combat-capable Runner (v4)
WebSocket client + REST API + decision engine + combat support
"""
import json, sys, os, time, logging, threading
from datetime import datetime, timezone
import requests
from decisions import decide_actions, parse_world_state, distance_hex
from memory import (
    load_state, save_state, log_action,
    update_balance, update_minerals, update_ships, update_units,
    update_planets, update_asteroids, update_stations,
    set_world_joined, set_starter_spawned
)

# ─── Config ──────────────────────────────────────────────────────────────────

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://crimsonmandate.com"
WS_URL = "wss://crimsonmandate.com/ws"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("runner")

# ─── REST API ────────────────────────────────────────────────────────────────

def api_get(path: str, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=15)
        return resp.json()
    except:
        return {}

def api_post(path: str, payload: dict, token: str):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    try:
        resp = requests.post(f"{BASE_URL}{path}", json=payload, headers=headers, timeout=15)
        return resp.json()
    except:
        return {}


# ─── WebSocket Client (async event-based) ────────────────────────────────────

class MMOClient:
    def __init__(self, token: str, session_id: str):
        self.token = token
        self.session_id = session_id
        self.authenticated = False
        self.world_joined = False
        self.running = False
        self.ws = None
        self.thread = None
        self._events = {}
        self._cv = threading.Condition()
        self._die = threading.Event()

    def start(self):
        import websocket
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        import websocket
        while self.running and not self._die.is_set():
            try:
                self.ws = websocket.WebSocketApp(
                    WS_URL,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=lambda ws, e: None,
                    on_close=lambda ws, *a: None,
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception:
                pass
            if self.running and not self._die.is_set():
                time.sleep(2)

    def _on_open(self, ws):
        self._send({"type": "auth", "payload": {"sessionId": self.token}})

    _golden_asteroid_spawned = None

    def _on_message(self, ws, msg):
        try:
            data = json.loads(msg)
        except:
            return
        msg_type = data.get("type", "unknown")
        payload = data.get("payload", data)

        with self._cv:
            self._events.setdefault(msg_type, []).append(payload)
            self._cv.notify_all()

        if msg_type == "auth_success":
            self.authenticated = True
            self._send({"type": "mmo_join_world", "payload": {"worldId": 1}})

        elif msg_type == "mmo_world_joined":
            self.world_joined = True

        elif msg_type == "mmo_resources":
            state = load_state()
            r = payload
            state["balance"]["isdBalance"] = r.get("isdBalance", 0)
            state["balance"]["credits"] = r.get("credits", 0)
            state["balance"]["minerals"] = r.get("minerals", 0)
            save_state(state)

        elif msg_type == "mmo_golden_asteroid_spawned":
            logger.warning(f"🌟 GOLDEN ASTEROID SPAWNED: {payload}")
            MMOClient._golden_asteroid_spawned = payload

        elif msg_type == "mmo_golden_asteroid_claimed":
            logger.info(f"🌟 GOLDEN ASTEROID CLAIMED: {payload}")

        elif msg_type == "mmo_mine_result":
            minerals = payload.get("mineralsGained", {})
            if minerals:
                logger.info(f"Mining yield: {minerals}")

        elif msg_type == "mmo_engagement_started":
            logger.info(f"⚔ Combat started: {payload.get('engagementId')}")

        elif msg_type == "mmo_combat_result":
            logger.info(f"⚔ Combat result: {payload}")

        elif msg_type == "mmo_unit_destroyed_notification":
            logger.info(f"💀 Unit destroyed: {payload.get('unitId')} by {payload.get('killedBy')}")

        elif msg_type == "mmo_loot_claimed":
            logger.info(f"🎁 Loot: {payload}")

        elif msg_type == "error":
            if payload.get("message"):
                logger.warning(f"Server error: {payload.get('message')}")

    def _on_error(self, ws, error):
        pass

    def _on_close(self, ws, *args):
        self.authenticated = False
        self.world_joined = False

    def _send(self, msg):
        if self.ws and self.running:
            try:
                self.ws.send(json.dumps(msg))
            except Exception:
                pass

    def wait_for(self, msg_type: str, timeout: float = 12.0) -> list:
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
        return bool(self.wait_for("auth_success", timeout))

    def get_world_state(self, timeout: float = 15.0) -> dict:
        """Get full parsed world state or empty dict."""
        msgs = self.wait_for("mmo_world_state", timeout)
        if not msgs:
            return {}
        return parse_world_state(msgs[-1])

    def wait_for_golden_asteroid(self, timeout: float = 300.0) -> dict:
        """Wait for a golden asteroid spawn event (up to 5 min)."""
        with self._cv:
            end = time.time() + timeout
            while time.time() < end:
                if MMOClient._golden_asteroid_spawned:
                    result = MMOClient._golden_asteroid_spawned
                    MMOClient._golden_asteroid_spawned = None
                    return result
                remaining = end - time.time()
                if remaining <= 0:
                    break
                self._cv.wait(timeout=min(remaining, 10.0))
            return None

    def wait_for_combat_result(self, timeout: float = 20.0) -> list:
        """Wait for combat events."""
        events = []
        end = time.time() + timeout
        while time.time() < end:
            with self._cv:
                for ev_type in ["mmo_engagement_started", "mmo_combat_result",
                                "mmo_unit_destroyed_notification", "mmo_loot_claimed"]:
                    if self._events.get(ev_type):
                        events.extend([(ev_type, p) for p in self._events.pop(ev_type)])
                if events:
                    break
                self._cv.wait(timeout=1.0)
        return events

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


# ─── Game Actions ────────────────────────────────────────────────────────────

def action_sync(state: dict, token: str) -> dict:
    """Sync state from REST API."""
    try:
        for path, key in [
            ("/api/profile/me", "commander_meta"),
            ("/api/profile/me/ships", "ships"),
            ("/api/balance", "balance"),
            ("/api/minerals/inventory", "minerals"),
            ("/api/components/inventory", "components"),
            ("/api/research/board", "research_board"),
        ]:
            data = api_get(path, token)
            # Only enforce success-check on endpoints that wrap in {"success": bool, "data": ...}
            needs_success = key not in ("components",)
            if not isinstance(data, dict):
                continue
            if needs_success and not data.get("success"):
                continue
            if key == "commander_meta":
                d = data.get("data", {})
                state["commander"]["shipCount"] = d.get("shipCount", 0)
            elif key == "ships":
                state = update_ships(state, data.get("ships", []))
            elif key == "balance":
                state = update_balance(state, data.get("data", {}))
            elif key == "minerals":
                state = update_minerals(state, data.get("minerals", []))
            elif key == "research_board":
                state["research_board"] = data if isinstance(data, list) else (data.get("data") or [])
            elif key == "components":
                components = data.get("components", []) if isinstance(data, dict) else []
                has_laser = any("mining laser" in c.get("name","").lower() for c in components)
                state["has_mining_laser"] = has_laser
                if has_laser:
                    state["mining_failures"] = 0
                    logger.info(f"✓ Mining Laser detected!")
    except Exception as e:
        logger.error(f"Sync error: {e}")
    return state


def action_sell_mineral(token: str, mineral_id: str, amount: int) -> dict:
    return api_post("/api/auction/list", {
        "mineralTypeId": mineral_id, "quantity": amount, "pricePerUnit": 0.3
    }, token)


def action_contribute_research(token: str, board_id: str, isd_amount: float) -> dict:
    return api_post("/api/research/contribute", {
        "boardId": board_id, "isdAmount": isd_amount
    }, token)


# ─── Combat Loop ─────────────────────────────────────────────────────────────

def execute_combat(token: str, session_id: str, scout: dict, enemies: list):
    """
    If scout is adjacent to enemy, attack. Otherwise move adjacent first.
    Fresh WS state fetched here to get real positions.
    Returns (attacked: bool, events: list)
    """
    if not enemies:
        return False, []

    target = enemies[0]

    # Fetch FRESH world state for current positions
    c = MMOClient(token, session_id)
    c.start()
    if not c.wait_for_auth(timeout=8):
        c.stop()
        return False, []
    fresh_ws = c.get_world_state(timeout=10)
    c.stop()

    # Find scout's current position from fresh state
    for u in fresh_ws.get("units", []):
        if u.get("id") == scout["id"]:
            scout_pos = u.get("position", scout.get("position", {}))
            break
    else:
        scout_pos = scout.get("position", {})

    tpos = target.get("position", {})
    dist = distance_hex(scout_pos, tpos)
    logger.info(f"Combat: Scout at {scout_pos}, target {target['id']} at {tpos}, dist={dist}")

    if dist <= 1:
        # Adjacent — attack directly
        c2 = MMOClient(token, session_id)
        c2.start()
        if not c2.wait_for_auth(timeout=8):
            c2.stop()
            return False, []
        _ = c2.get_world_state(timeout=10)
        logger.info(f"⚔ Attacking {target['id']} (dist={dist})")
        c2._send({"type": "mmo_attack", "payload": {
            "attackerId": scout["id"],
            "targetId": target["id"],
            "position": tpos
        }})
        events = c2.wait_for_combat_result(timeout=20)
        c2.stop()
        return True, events

    elif dist <= 20:
        # Move to an adjacent hex (one step toward target)
        # Use axial direction: move one step in direction of target
        q_diff = tpos.get("q", 0) - scout_pos.get("q", 0)
        r_diff = tpos.get("r", 0) - scout_pos.get("r", 0)
        # Normalize to one step
        step_q = 0 if q_diff == 0 else (1 if q_diff > 0 else -1)
        step_r = 0 if r_diff == 0 else (1 if r_diff > 0 else -1)
        move_target = {
            "q": scout_pos.get("q", 0) + step_q,
            "r": scout_pos.get("r", 0) + step_r
        }
        logger.info(f"→ Moving Scout toward {move_target} (dist={dist})")

        c2 = MMOClient(token, session_id)
        c2.start()
        if not c2.wait_for_auth(timeout=8):
            c2.stop()
            return False, []
        _ = c2.get_world_state(timeout=10)
        c2._send({"type": "mmo_move_unit", "payload": {
            "unitId": scout["id"],
            "targetHex": move_target
        }})
        c2.wait_for("mmo_unit_moved", timeout=15)
        c2.stop()
        # Movement executed — combat not resolved this cycle
        return False, []

    return False, []


# ─── Main Cycle ───────────────────────────────────────────────────────────────

def run_cycle():
    logger.info("═══ Crimson Mandate Agent Cycle ═══")

    state = load_state()
    token = state.get("session", {}).get("token", "")
    session_id = state.get("session", {}).get("sessionId", "")

    if not token or not session_id:
        logger.error("No session — run auth.py first")
        return

    # REST sync
    state = action_sync(state, token)
    save_state(state)
    logger.info(f"Balance: ISD {state.get('balance',{}).get('isdBalance',0)} | "
                f"Credits {state.get('balance',{}).get('credits',0)}")

    # WebSocket world state
    client = MMOClient(token, session_id)
    client.start()
    if not client.wait_for_auth(timeout=10):
        logger.warning("WS Auth timeout")
        client.stop()
        return

    ws_state = client.get_world_state(timeout=15)
    client.stop()

    if not ws_state:
        logger.warning("No world state received")
        return

    user_id = state["commander"]["userId"]
    units = ws_state.get("units", [])
    planets = ws_state.get("planets", [])
    asteroids = ws_state.get("asteroids", [])
    owned = [u for u in units if u.get("ownerId") == user_id]

    # Update state
    state = update_units(state, units)
    state = update_planets(state, planets)
    state = update_asteroids(state, asteroids)
    if owned:
        state = set_starter_spawned(state)
    state = set_world_joined(state)
    save_state(state)

    logger.info(f"Owned: {len(owned)} units | Asteroids: {len(asteroids)} | Planets: {len(planets)}")

    # ── Combat: Attack nearby enemies if scout is available ──
    scout = next((u for u in owned if u.get("type") == "Scout"), None)
    combat_happened = False
    if scout:
        edf = [u for u in units if u.get("ownerName") == "Earth Defense Force"]
        scout_pos = scout.get("position", {})
        enemies = sorted(edf, key=lambda e: distance_hex(scout_pos, e.get("position", {})))

        if enemies:
            attacked, combat_events = execute_combat(token, session_id, scout, enemies)
            for ev_type, ev_payload in combat_events:
                state = log_action(state, ev_type, str(ev_payload), "ok")
                combat_happened = True

    # ── Decision engine — only if combat didn't consume the cycle ──
    if not combat_happened:
        actions = decide_actions(state, ws_state)
        logger.info(f"Decision: {[a['type'] for a in actions]}")
    else:
        logger.info("Combat happened — skipping decision engine this cycle")
        actions = []

    # ── Execute actions ──
    for action in actions:
        atype = action["type"]
        payload = action["payload"]

        try:
            if action.get("ws"):
                ws_msg_type = {
                    "mine_asteroid": "mmo_mine_asteroid",
                    "move_unit": "mmo_move_unit",
                }.get(atype, atype)

                c = MMOClient(token, session_id)
                c.start()
                if not c.wait_for_auth(timeout=8):
                    state = log_action(state, atype, "auth failed", "error")
                    c.stop()
                    continue
                _ = c.get_world_state(timeout=10)
                c._send({"type": ws_msg_type, "payload": payload})

                # Track position after move optimistically
                if atype == "move_unit":
                    move_target = payload.get("targetHex", {})
                    for u in state.get("units", []):
                        if u.get("id") == payload.get("unitId"):
                            u["position"] = move_target
                            break

                time.sleep(3)
                
                # Track mining failures
                if atype == "mine_asteroid":
                    # Check components for Mining Laser
                    comp_resp = api_get("/api/components/inventory", token)
                    if comp_resp.get("success"):
                        components = comp_resp.get("components", [])
                        has_laser = any("mining laser" in c.get("name","").lower() for c in components)
                        if has_laser:
                            state["has_mining_laser"] = True
                            state["mining_failures"] = 0
                            logger.info("✓ Mining Laser detected!")
                        else:
                            # Increment failure counter
                            state["mining_failures"] = state.get("mining_failures", 0) + 1
                            if state["mining_failures"] >= 3:
                                logger.warning("Mining Laser missing — 3 failures. Blocking mining.")
                
                c.stop()
                state = log_action(state, atype, str(payload), "ok")

            elif atype == "sell":
                result = action_sell_mineral(token, payload["mineralTypeId"], payload["amount"])
                state = log_action(state, "sell",
                    f"{payload['mineralTypeId']} x{payload['amount']}",
                    "ok" if result.get("success") else f"error: {result.get('error',{}).get('message','?')}")

            elif atype == "contribute_research":
                result = action_contribute_research(token, payload["boardId"], payload["isdAmount"])
                state = log_action(state, "contribute_research",
                    f"{payload['isdAmount']} ISD",
                    "ok" if result.get("success") else f"error: {result.get('error',{}).get('message','?')}")

        except Exception as e:
            logger.error(f"Action '{atype}' error: {e}")
            state = log_action(state, atype, str(e), "error")

    # Final sync
    state = action_sync(state, token)
    state["lastRun"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    logger.info(f"═══ Cycle complete ═══")


if __name__ == "__main__":
    run_cycle()