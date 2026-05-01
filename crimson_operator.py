#!/usr/bin/env python3
"""
Crimson Mandate — Autonomous Operator (HAL-P owned)
Runs the 5-minute grind cycle forever, messages HAL-P main session on significant events.
"""
import os, sys, json, time, requests, datetime as dt
from pathlib import Path

AGENT_DIR = "/Users/jonathan/.openclaw/workspace/crimson-mandate-agent"
STATE_FILE = os.path.join(AGENT_DIR, "state.json")
LOG_FILE = os.path.join(AGENT_DIR, "operator.log")
ALERT_FILE = "/tmp/crimson_mandate_alerts.json"
STATUS_FILE = "/tmp/crimson_last_status.txt"
SESSION_KEY = "agent:main:discord:direct:148191845040652288"
OPENCLAW_BASE = "http://localhost:18789"

BASE = "https://crimsonmandate.com"

sys.path.insert(0, AGENT_DIR)
from memory import load_state, save_state, log_action
from runner import MMOClient, action_sync, execute_combat, distance_hex

# ─── Logging ──────────────────────────────────────────────────────────────────

def log(msg):
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line)
    Path(LOG_FILE).open("a").write(line + "\n")

def _last_status_time() -> float:
    """Read last status epoch from tracking file; returns 0 if missing/empty."""
    try:
        return float(Path(STATUS_FILE).read_text().strip())
    except Exception:
        return 0.0

def _write_last_status_time(ts: float):
    """Write current epoch to tracking file."""
    Path(STATUS_FILE).write_text(str(ts))


def message_halp(text: str):
    """Message HAL-P directly on Discord via sessions_send."""
    try:
        import urllib.request
        req = urllib.request.Request(
            f"http://localhost:18789/api/sessions",
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
            log(f"[HAL-P] No main session found")
            return
        import urllib.request
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

# ─── Cycle ───────────────────────────────────────────────────────────────────

def run_cycle(cycle_num: int):
    log(f"═══ Cycle {cycle_num} starting ═══")

    state = load_state()
    token = state.get("session", {}).get("token", "")
    session_id = state.get("session", {}).get("sessionId", "")

    if not token:
        msg = "Crimson Mandate — No session token. Run auth.py first."
        log(msg)
        message_halp(msg)
        return False

    # REST sync
    state = action_sync(state, token)
    save_state(state)

    balance = state.get("balance", {})
    prev_isd = state.get("balance", {}).get("isdBalance", 0)
    isd = balance.get("isdBalance", 0)
    credits = balance.get("credits", 0)
    has_laser = state.get("has_mining_laser", False)
    mining_failures = state.get("mining_failures", 0)

    log(f"Balance: ISD={isd}, Credits={credits}, Laser={has_laser}, Failures={mining_failures}")

    # WebSocket world state
    client = MMOClient(token, session_id)
    client.start()
    if not client.wait_for_auth(timeout=10):
        log("WS Auth timeout")
        client.stop()
        return False

    ws_state = client.get_world_state(timeout=15)
    client.stop()

    if not ws_state:
        log("No world state")
        return False

    user_id = state["commander"]["userId"]
    units = ws_state.get("units", [])
    planets = ws_state.get("planets", [])
    asteroids = ws_state.get("asteroids", [])
    owned = [u for u in units if u.get("ownerId") == user_id]

    scout = next((u for u in owned if u.get("type") == "Scout"), None)
    scout_pos = scout.get("position", {}) if scout else {}
    scout_hp = scout.get("currentHp", 0) if scout else 0

    edf = [u for u in units if u.get("ownerName") == "Earth Defense Force"]
    fighters = [e for e in edf if "Fighter" in e.get("type", "")]
    cruisers = [e for e in edf if "Cruiser" in e.get("type", "")]

    action_taken = ""
    significant = False

    # ── Decision ──
    if not scout:
        action_taken = "Scout dead — waiting for respawn"
        significant = True

    elif isd >= 1000 and not has_laser:
        action_taken = f"1000 ISD reached — READY TO BUY LASER"
        significant = True
        message_halp(f"Crimson Mandate — 1000 ISD reached! Ready to purchase Mining Laser Mk1.")

    elif fighters and scout_hp >= 20:
        # ── Priority 3: Attack EDF Fighters ──
        target = min(fighters, key=lambda e: distance_hex(scout_pos, e.get("position", {})))
        log(f"Attacking Fighter at {target.get('position')} HP={target.get('currentHp')}")
        attacked, events = execute_combat(token, session_id, scout, [target])

        if attacked:
            destroyed = any(t == "mmo_unit_destroyed_notification" for t, _ in events)
            loot = any(t == "mmo_loot_claimed" for t, _ in events)
            loot_detail = ""
            for t, p in events:
                if t == "mmo_loot_claimed":
                    loot_detail = f" → Loot: {p.get('type','?')} x{p.get('quantity','?')}"
                    significant = True

            action_taken = f"Fighter → destroyed={destroyed} loot={loot}{loot_detail}"
            log(action_taken)

            for ev_type, ev_payload in events:
                state = log_action(state, ev_type, str(ev_payload), "ok")

            if destroyed:
                message_halp(f"Crimson — Fighter destroyed! ISD={isd} Credits={credits}. {loot_detail}")
        else:
            action_taken = "Approaching Fighter"

    elif not fighters and scout:
        # ── Priority 4: Scout idle — check golden asteroid, then stay ──
        # Highest-value ISD opportunity: golden asteroid spawns
        golden = MMOClient._golden_asteroid_spawned
        if golden:
            gpos = golden.get("position", {})
            if gpos:
                dist = distance_hex(scout_pos, gpos)
                log(f"Golden asteroid at {gpos}, dist={dist}")
                if dist <= 1:
                    # Claim it
                    client2 = MMOClient(token, session_id)
                    client2.start()
                    if client2.wait_for_auth(timeout=8):
                        _ = client2.get_world_state(timeout=10)
                        client2._send({"type": "mmo_claim_golden_asteroid", "payload": {"asteroidId": golden["id"]}})
                        result = client2.wait_for("mmo_golden_asteroid_claimed", timeout=15)
                        log(f"Golden claim result: {result}")
                        if result:
                            for r in result:
                                if isinstance(r, dict) and r.get("cryptoRewarded"):
                                    amt = r.get("cryptoRewarded", 0)
                                    significant = True
                                    message_halp(f"Crimson — Golden asteroid claimed! ~{amt} ISD earned!")
                                    state = action_sync(state, token)
                                    isd = state.get("balance", {}).get("isdBalance", isd)
                    client2.stop()
                elif dist <= 20:
                    # Move toward golden asteroid
                    client2 = MMOClient(token, session_id)
                    client2.start()
                    if client2.wait_for_auth(timeout=8):
                        _ = client2.get_world_state(timeout=10)
                        client2._send({"type": "mmo_move_unit", "payload": {
                            "unitId": scout["id"],
                            "targetHex": gpos
                        }})
                        client2.wait_for("mmo_unit_moved", timeout=15)
                    client2.stop()
                    action_taken = f"Moving to golden asteroid (dist={dist})"
                    log(action_taken)
                    state = action_sync(state, token)
                    state["lastRun"] = dt.datetime.now(dt.timezone.utc).isoformat()
                    save_state(state)
                    return True

        if mining_failures >= 5:
            # Circuit breaker: stop burning ISD when Basic Mining Array can't extract anything
            log(f"Circuit breaker: {mining_failures} mining failures — scout staying idle at ({scout_pos.get('q')},{scout_pos.get('r')})")
            state["lastRun"] = dt.datetime.now(dt.timezone.utc).isoformat()
            save_state(state)
            return True
        elif scout_pos.get('q', 0) != 12 or scout_pos.get('r', 0) != -5:
            client_exp = MMOClient(token, session_id)
            client_exp.start()
            if client_exp.wait_for_auth(timeout=8):
                _ = client_exp.get_world_state(timeout=10)
                client_exp._send({"type": "mmo_move_unit", "payload": {
                    "unitId": scout["id"] if scout else state.get('scout_id', ''),
                    "targetHex": {"q": 12, "r": -5}
                }})
                client_exp.wait_for("mmo_unit_moved", timeout=15)
                log(f"Exploring: moving scout to Mars area (12,-5)")
            client_exp.stop()
            state = action_sync(state, token)
            state["lastRun"] = dt.datetime.now(dt.timezone.utc).isoformat()
            save_state(state)
            return True

    elif has_laser and asteroids:
        # ── Priority 5: Mine tier-1 asteroids ──
        tier1 = [a for a in asteroids if not a.get("isDepleted") and a.get("miningLevel", 0) >= 1]
        if tier1:
            target = min(tier1, key=lambda a: distance_hex(scout_pos, a.get("position", {})))
            dist = distance_hex(scout_pos, target.get("position", {}))
            if dist <= 1:
                client3 = MMOClient(token, session_id)
                client3.start()
                if client3.wait_for_auth(timeout=8):
                    _ = client3.get_world_state(timeout=10)
                    client3._send({"type": "mmo_mine_asteroid", "payload": {
                        "unitId": scout["id"],
                        "asteroidId": target["id"]
                    }})
                client3.stop()
                action_taken = f"Mining tier-1 asteroid"
                state = log_action(state, "mine_asteroid", f"asteroid {target['id']}", "ok")
            else:
                client3 = MMOClient(token, session_id)
                client3.start()
                if client3.wait_for_auth(timeout=8):
                    _ = client3.get_world_state(timeout=10)
                    client3._send({"type": "mmo_move_unit", "payload": {
                        "unitId": scout["id"],
                        "targetHex": target.get("position", {})
                    }})
                    client3.wait_for("mmo_unit_moved", timeout=15)
                client3.stop()
                action_taken = "Moving to tier-1 asteroid"
        else:
            action_taken = "No tier-1 asteroids visible"

    else:
        action_taken = f"Idle — HP={scout_hp} Fighters={len(fighters)} Laser={has_laser}"

    # ── Final sync ──
    state = action_sync(state, token)
    state["lastRun"] = dt.datetime.now(dt.timezone.utc).isoformat()
    save_state(state)

    log(f"═══ Cycle {cycle_num} done: {action_taken} ═══")

    # ── 5-minute status update to HAL-P ──
    fighters = [e for e in edf if "Fighter" in e.get("type", "")]
    now = time.time()
    if now - _last_status_time() >= 300:
        status_msg = (
            f"[Crimson Status] Cycle {cycle_num} | ISD={isd} | Credits={credits} | "
            f"Laser={has_laser} | Failures={mining_failures} | Fighters={len(fighters)}"
        )
        message_halp(status_msg)
        _write_last_status_time(now)

    return True

# ─── Main Loop ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log("Starting Crimson Mandate Autonomous Operator")
    log(f"Owner: HAL-P | Cycle interval: 5 minutes")

    cycle_num = 0
    consecutive_errors = 0

    while True:
        cycle_num += 1
        try:
            ok = run_cycle(cycle_num)
            if ok:
                consecutive_errors = 0
            else:
                consecutive_errors += 1
        except Exception as e:
            log(f"CYCLE ERROR: {e}")
            message_halp(f"Crimson Mandate — Cycle {cycle_num} crashed: {e}")
            consecutive_errors += 1

        if consecutive_errors >= 3:
            msg = f"Crimson Mandate — 3 consecutive errors — stopping and escalating."
            log(msg)
            message_halp(msg)
            break

        time.sleep(300)  # 5 minutes
