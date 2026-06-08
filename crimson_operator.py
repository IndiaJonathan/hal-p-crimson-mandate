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

    # REST sync — action_sync resets mining_failures on ok results
    state = action_sync(state, token)
    save_state(state)  # save after action_sync (resets mining_failures on ok)

    balance = state.get("balance", {})
    prev_isd = state.get("balance", {}).get("isdBalance", 0)
    isd = balance.get("isdBalance", 0)
    credits = balance.get("credits", 0)
    has_laser = state.get("has_mining_laser", False)

    log(f"Balance: ISD={isd}, Credits={credits}, Laser={has_laser}, Failures={state.get('mining_failures', 0)}")

    # WebSocket world state
    client = MMOClient(token, session_id)
    client.start()
    if not client.wait_for_auth(timeout=30):
        log("WS Auth timeout")
        client.stop()
        return False

    # Detect server token rejection — re-auth if isAuthenticated=False
    if not client.authenticated:
        log("WS Auth rejected — server rejected token. Re-authing...")
        client.stop()
        import subprocess
        auth_result = subprocess.run(
            [sys.executable, os.path.join(AGENT_DIR, "auth.py")],
            capture_output=True, text=True, cwd=AGENT_DIR
        )
        log(f"Re-auth result: {auth_result.stdout.strip()}")
        if auth_result.returncode != 0:
            log(f"Re-auth failed: {auth_result.stderr}")
            return False
        # Reload fresh state and restart operator with new token
        state = load_state()
        token = state.get("session", {}).get("token", "")
        session_id = state.get("session", {}).get("sessionId", "")
        log(f"Re-authed. Sleeping 90s before restart to break re-auth loop...")
        time.sleep(90)
        log(f"Re-authed. Restarting with sessionId={session_id[:8]}...")
        os.execv(sys.executable, [sys.executable, os.path.join(AGENT_DIR, "crimson_operator.py")])

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
                    if client2.wait_for_auth(timeout=20):
                        _ = client2.get_world_state(timeout=15)
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
                    if client2.wait_for_auth(timeout=20):
                        _ = client2.get_world_state(timeout=15)
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

        # Determine if scout is currently at a tier-0 asteroid (can mine with Basic Mining Array)
        tier0_near = [
            a for a in (ws_state.get('asteroids') or [])
            if not a.get('isDepleted') and a.get('miningLevel', 0) == 0
            and a.get('requiredComponentId') is None
            and distance_hex(scout.get('position', {}), a.get('position', {})) <= 1
        ]
        mining = bool(tier0_near)

        # ── Circuit breaker: check BEFORE action_sync (which resets failures to 0 on ok) ──
        # Without this ordering, the check always sees 0 and never triggers.
        if scout and state.get('mining_failures', 0) >= 20:
            log(f"Circuit breaker: {state.get('mining_failures', 0)} mining failures — staying put")
            state = action_sync(state, token)
            save_state(state)
            return True

        # ── Stuck cycling detector: same target moved toward 3+ times without mining ──
        # Break infinite loops by tracking consecutive move_unit toward same asteroid.
        stuck_target = state.get('stuck_target', '')
        stuck_count = state.get('stuck_count', 0)
        last_target = state.get('last_move_target', '')

        # ── Tier-0 mining or explore ──
        # Mine tier-0 asteroid if scout is adjacent; otherwise explore toward Mars
        # to find new asteroids. Circuit breaker (above) suppresses mining when failures are high.
        if scout and tier0_near:
            # Mine tier-0 asteroid with Basic Mining Array
            target = tier0_near[0]
            log(f"Mining tier-0 asteroid {target['id']} (Basic Mining Array)")
            client_m = MMOClient(token, session_id)
            client_m.start()
            if client_m.wait_for_auth(timeout=20):
                _ = client_m.get_world_state(timeout=15)
                client_m._send({"type": "mmo_mine_asteroid", "payload": {
                    "unitId": scout["id"],
                    "asteroidId": target["id"]
                }})
                client_m.wait_for("mmo_asteroid_mined", timeout=15)
            client_m.stop()
            action_taken = f"Mining tier-0 asteroid {target['id']}"
            # Clear stuck tracker on successful mine
            state['stuck_target'] = ''
            state['stuck_count'] = 0
            state['last_move_target'] = ''
            state = action_sync(state, token)
            state['lastRun'] = dt.datetime.now(dt.timezone.utc).isoformat()
            save_state(state)
            return True
        elif scout and scout_pos and distance_hex(scout_pos, {"q": 0, "r": 0}) > 20:
            # Scout is far from home — don't drift to Mars, stay put
            log(f"Scout far from origin — staying at current position")
            state = action_sync(state, token)
            state['lastRun'] = dt.datetime.now(dt.timezone.utc).isoformat()
            save_state(state)
            return True
        else:
            # Default: explore toward Mars to find new asteroids
            # But first check if we're stuck cycling toward the same target
            tier0_all = [
                a for a in (ws_state.get('asteroids') or [])
                if not a.get('isDepleted') and a.get('miningLevel', 0) == 0
                and a.get('requiredComponentId') is None
            ]
            # Pick a different asteroid if stuck on current target
            explore_target = {"q": 12, "r": -5}  # default Mars
            if tier0_all:
                if stuck_target and stuck_count >= 3:
                    # Try a different tier-0 asteroid instead of the stuck one
                    others = [a for a in tier0_all if a['id'] != stuck_target]
                    if others:
                        alt = others[0]
                        explore_target = alt.get('position', {"q": 12, "r": -5})
                        log(f"Stuck on {stuck_target} ({stuck_count}x) — diverting to {alt['id']} at ({explore_target['q']},{explore_target['r']})")
                    else:
                        log(f"Stuck on {stuck_target} ({stuck_count}x) — no alternate asteroid, going to Mars")
                else:
                    # Normal: move toward nearest tier-0 asteroid
                    nearest = min(tier0_all, key=lambda a: distance_hex(scout_pos or {"q":0,"r":0}, a.get('position', {})))
                    explore_target = nearest.get('position', {"q": 12, "r": -5})
                    # Track stuck count
                    if last_target == nearest['id']:
                        state['stuck_count'] = stuck_count + 1
                        state['stuck_target'] = nearest['id']
                    else:
                        state['stuck_count'] = 1
                        state['stuck_target'] = nearest['id']
                    state['last_move_target'] = nearest['id']
            client_exp = MMOClient(token, session_id)
            client_exp.start()
            if client_exp.wait_for_auth(timeout=20):
                _ = client_exp.get_world_state(timeout=15)
                client_exp._send({"type": "mmo_move_unit", "payload": {
                    "unitId": scout["id"] if scout else state.get('scout_id', ''),
                    "targetHex": explore_target
                }})
                client_exp.wait_for("mmo_unit_moved", timeout=15)
                log(f"Exploring: moving scout to ({explore_target['q']},{explore_target['r']})")
            client_exp.stop()
            state = action_sync(state, token)
            state['lastRun'] = dt.datetime.now(dt.timezone.utc).isoformat()
            save_state(state)
            return True

        # ── Tier-0 mining or explore ──
        # Mine tier-0 asteroid if scout is adjacent; otherwise explore toward Mars
        # to find new asteroids. Circuit breaker (above) suppresses mining when failures are high.
        if scout and tier0_near:
            # Mine tier-0 asteroid with Basic Mining Array
            target = tier0_near[0]
            log(f"Mining tier-0 asteroid {target['id']} (Basic Mining Array)")
            client_m = MMOClient(token, session_id)
            client_m.start()
            if client_m.wait_for_auth(timeout=20):
                _ = client_m.get_world_state(timeout=15)
                client_m._send({"type": "mmo_mine_asteroid", "payload": {
                    "unitId": scout["id"],
                    "asteroidId": target["id"]
                }})
                client_m.wait_for("mmo_asteroid_mined", timeout=15)
            client_m.stop()
            action_taken = f"Mining tier-0 asteroid {target['id']}"
            state = action_sync(state, token)
            state["lastRun"] = dt.datetime.now(dt.timezone.utc).isoformat()
            save_state(state)
            return True
        elif scout and scout_pos and distance_hex(scout_pos, {"q": 0, "r": 0}) > 20:
            # Scout is far from home — don't drift to Mars, stay put
            log(f"Scout far from origin — staying at current position")
            state["lastRun"] = dt.datetime.now(dt.timezone.utc).isoformat()
            save_state(state)
            return True
        else:
            # Default: explore toward Mars to find new asteroids
            client_exp = MMOClient(token, session_id)
            client_exp.start()
            if client_exp.wait_for_auth(timeout=20):
                _ = client_exp.get_world_state(timeout=15)
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
                if client3.wait_for_auth(timeout=20):
                    _ = client3.get_world_state(timeout=15)
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
                if client3.wait_for_auth(timeout=20):
                    _ = client3.get_world_state(timeout=15)
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
            f"Laser={has_laser} | Failures={state.get('mining_failures', 0)} | Fighters={len(fighters)}"
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
