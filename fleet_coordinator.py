#!/usr/bin/env python3
"""
Crimson Mandate — Fleet Coordinator
Manages multiple account agents, coordinates movement and attacks.
"""
import json, os, time, requests, websocket, threading, datetime

BASE = "https://crimsonmandate.com"
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(AGENT_DIR, "fleet_credentials.json")

# ─── Credentials ───────────────────────────────────────────────────────────────

def load_fleet():
    """Load all account credentials."""
    creds = {"accounts": []}
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE) as f:
            creds = json.load(f)
    
    accounts = []
    # Primary account from state.json
    state_file = os.path.join(AGENT_DIR, "state.json")
    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
        accounts.append({
            "email": state["commander"].get("email", "halp@burk-dashboards.com"),
            "name": "HALP-1",
            "token": state["session"]["token"],
            "userId": state["commander"]["userId"]
        })
    
    # Additional accounts
    for a in creds.get("accounts", []):
        accounts.append(a)
    return accounts


def register_account(email, commander_name):
    """Register + login a new account. Returns (token, user_id)."""
    r = requests.post(f"{BASE}/api/auth/register", json={
        "commanderName": commander_name,
        "email": email,
        "password": "Test1234!",
        "passwordConfirm": "Test1234!",
        "tosAccepted": True
    }, timeout=10)
    d = r.json()
    if not d.get("success"):
        return None
    
    # Login to get token
    r2 = requests.post(f"{BASE}/api/auth/login", json={
        "email": email, "password": "Test1234!"
    }, timeout=10)
    d2 = r2.json()
    if not d2.get("success"):
        return None
    
    return d2["data"]["token"], d2["data"]["userId"]


def login_account(email):
    r = requests.post(f"{BASE}/api/auth/login", json={
        "email": email, "password": "Test1234!"
    }, timeout=10)
    d = r.json()
    if d.get("success"):
        return d["data"]["token"], d["data"]["userId"]
    return None, None


def save_accounts(accounts):
    """Save extra accounts (not primary) to credentials file."""
    extra = [a for a in accounts if a["email"] != "halp@burk-dashboards.com"]
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump({"accounts": extra}, f, indent=2)


# ─── World State ───────────────────────────────────────────────────────────────

def get_world_state(token):
    """Get full world state via WebSocket. Returns (units, planets, asteroids)."""
    result = {"units": [], "planets": [], "asteroids": [], "done": threading.Event()}
    
    def on_message(ws, msg):
        data = json.loads(msg)
        if data.get("type") == "mmo_world_state":
            for chunk in data["payload"].get("chunks", []):
                result["units"].extend(chunk.get("units", []))
                result["planets"].extend(chunk.get("planets", []))
                result["asteroids"].extend(chunk.get("asteroids", []))
            result["done"].set()
    
    ws = websocket.WebSocketApp(
        "wss://crimsonmandate.com/ws",
        on_message=on_message,
        on_close=lambda ws, *a: result["done"].set()
    )
    def on_open(ws):
        ws.send(json.dumps({"type": "auth", "payload": {"sessionId": token}}))
        time.sleep(0.5)
        ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
    ws.on_open = on_open
    t = threading.Thread(target=ws.run_forever, daemon=True)
    t.start()
    result["done"].wait(timeout=12)
    ws.close()
    return result["units"], result["planets"], result["asteroids"]


def cube_dist(p1, p2):
    def cube(q, r): return (q, -q-r, r)
    c1 = cube(p1.get("q", 0), p1.get("r", 0))
    c2 = cube(p2.get("q", 0), p2.get("r", 0))
    return max(abs(c1[i] - c2[i]) for i in range(3))


# ─── Movement & Combat ────────────────────────────────────────────────────────

def move_unit(token, unit_id, target_hex, wait=8):
    """Move a unit to target hex."""
    done = threading.Event()
    
    def on_message(ws, msg):
        data = json.loads(msg)
        if data.get("type") in ("mmo_unit_moved", "mmo_resources"):
            done.set()
    
    ws = websocket.WebSocketApp(
        "wss://crimsonmandate.com/ws",
        on_message=on_message,
        on_close=lambda ws, *a: done.set()
    )
    def on_open(ws):
        ws.send(json.dumps({"type": "auth", "payload": {"sessionId": token}}))
        time.sleep(0.5)
        ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
        time.sleep(1)
        ws.send(json.dumps({"type": "mmo_move_unit", "payload": {"unitId": unit_id, "targetHex": target_hex}}))
        time.sleep(wait)
        done.set()
    ws.on_open = on_open
    t = threading.Thread(target=ws.run_forever, daemon=True)
    t.start()
    done.wait(timeout=wait + 5)
    ws.close()


def attack_target(token, attacker_id, target_id, target_pos, wait=20):
    """Attack a target. Returns list of (event_type, payload) tuples."""
    events = []
    done = threading.Event()
    
    def on_message(ws, msg):
        data = json.loads(msg)
        t = data.get("type", "?")
        p = data.get("payload", data)
        if t not in ("connected", "pong", "auth_success", "mmo_world_state",
                     "mmo_tick_update", "ftue_guidance", "mmo_resources"):
            print(f"  [{t}]: {str(p)[:100]}")
            events.append((t, p))
        if t in ("mmo_combat_result", "mmo_unit_destroyed_notification",
                  "mmo_engagement_started", "mmo_loot_claimed"):
            done.set()
    
    ws = websocket.WebSocketApp(
        "wss://crimsonmandate.com/ws",
        on_message=on_message,
        on_close=lambda ws, *a: done.set()
    )
    def on_open(ws):
        ws.send(json.dumps({"type": "auth", "payload": {"sessionId": token}}))
        time.sleep(0.5)
        ws.send(json.dumps({"type": "mmo_join_world", "payload": {"worldId": 1}}))
        time.sleep(2)
        ws.send(json.dumps({"type": "mmo_attack", "payload": {
            "attackerId": attacker_id,
            "targetId": target_id,
            "position": target_pos
        }}))
        time.sleep(wait)
        done.set()
    ws.on_open = on_open
    t = threading.Thread(target=ws.run_forever, daemon=True)
    t.start()
    done.wait(timeout=wait + 5)
    ws.close()
    return events


# ─── Fleet Status ─────────────────────────────────────────────────────────────

def fleet_status():
    """Show status of all fleet accounts."""
    accounts = load_fleet()
    print(f"\n═══ Fleet Status ({len(accounts)} accounts) ═══")
    
    for acct in accounts:
        units, planets, asteroids = get_world_state(acct["token"])
        our = [u for u in units if u.get("ownerId") == acct["userId"]]
        edf = [u for u in units if u.get("ownerName") == "Earth Defense Force"]
        
        scout = next((u for u in our if u.get("type") == "Scout"), our[0] if our else None)
        scout_pos = scout.get("position", "unknown") if scout else "none"
        
        # Closest EDF to this scout
        closest_edf = None
        if scout and edf:
            closest_edf = min(edf, key=lambda e: cube_dist(scout.get("position", {}), e.get("position", {})))
        
        print(f"\n  {acct['name']} ({acct['email']})")
        print(f"    Scout: {scout_pos} ({len(our)} unit{'s' if len(our)!=1 else ''})")
        print(f"    EDF visible: {len(edf)}")
        if closest_edf:
            d = cube_dist(scout.get("position", {}), closest_edf.get("position", {}))
            print(f"    Closest EDF: {closest_edf['type']} at {closest_edf['position']} (dist={d})")
    
    return accounts


# ─── Fleet Attack ─────────────────────────────────────────────────────────────

def fleet_attack(target_edf_id, target_pos):
    """All fleet accounts attack the same EDF target simultaneously."""
    accounts = load_fleet()
    print(f"\n═══ Fleet Attack on {target_edf_id} at {target_pos} ═══")
    
    threads = []
    results = {}
    
    def attack(acct):
        scout = None
        units, _, _ = get_world_state(acct["token"])
        our = [u for u in units if u.get("ownerId") == acct["userId"]]
        scout = next((u for u in our if u.get("type") == "Scout"), our[0] if our else None)
        
        if not scout:
            results[acct["name"]] = "NO SCOUT"
            return
        
        # Check if adjacent
        dist = cube_dist(scout.get("position", {}), target_pos)
        if dist > 2:
            print(f"  {acct['name']}: Scout at {scout.get('position')} — too far (dist={dist}), moving...")
            move_unit(acct["token"], scout["id"], target_pos)
            # Re-fetch position
            units2, _, _ = get_world_state(acct["token"])
            our2 = [u for u in units2 if u.get("ownerId") == acct["userId"]]
            scout2 = next((u for u in our2 if u.get("type") == "Scout"), our2[0] if our2 else None)
            if scout2:
                scout = scout2
        
        if scout:
            print(f"  {acct['name']}: Attacking from {scout.get('position')}...")
            events = attack_target(acct["token"], scout["id"], target_edf_id, target_pos, wait=25)
            results[acct["name"]] = events
        else:
            results[acct["name"]] = "NO SCOUT AFTER MOVE"
    
    # Launch all attacks in parallel
    for acct in accounts:
        t = threading.Thread(target=lambda a=acct: attack(a))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()
    
    print("\n─── Results ───")
    for name, result in results.items():
        if isinstance(result, str):
            print(f"  {name}: {result}")
        else:
            destroyed = any(t == "mmo_unit_destroyed_notification" for t, _ in result)
            loot = any(t == "mmo_loot_claimed" for t, _ in result)
            print(f"  {name}: events={len(result)} destroyed={destroyed} loot={loot}")
            for t, p in result:
                print(f"    [{t}]: {str(p)[:100]}")
    
    return results


# ─── Add Account ───────────────────────────────────────────────────────────────

def add_account(email, name):
    """Register and add a new account to the fleet."""
    print(f"Registering {email} ({name})...")
    result = register_account(email, name)
    if result:
        token, user_id = result
        # Save to credentials
        creds = {"accounts": []}
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE) as f:
                creds = json.load(f)
        creds["accounts"].append({
            "email": email,
            "name": name,
            "token": token,
            "userId": user_id
        })
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(creds, f, indent=2)
        print(f"✓ {name} added. Token: {token[:30]}...")
        return True
    else:
        print(f"✗ Failed to register {email}")
        return False


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 fleet_coordinator.py <command>")
        print("Commands:")
        print("  status              — Show fleet positions and EDF targets")
        print("  attack <id> <q> <r> — All accounts attack EDF at (q,r)")
        print("  add <email> <name>  — Add new account to fleet")
        print("  register_more       — Register 3 more accounts (HALP-2,3,4)")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        fleet_status()
    
    elif cmd == "register_more":
        emails = [
            ("halp2@burk-dashboards.com", "HALP-Viper-2"),
            ("halp3@burk-dashboards.com", "HALP-Viper-3"),
            ("halp4@burk-dashboards.com", "HALP-Viper-4"),
        ]
        for email, name in emails:
            add_account(email, name)
            time.sleep(1)
        fleet_status()
    
    elif cmd == "add":
        if len(sys.argv) < 4:
            print("Usage: fleet_coordinator.py add <email> <name>")
            sys.exit(1)
        add_account(sys.argv[2], sys.argv[3])
    
    elif cmd == "attack":
        if len(sys.argv) < 5:
            print("Usage: fleet_coordinator.py attack <edf_id> <q> <r>")
            sys.exit(1)
        target_id = sys.argv[2]
        target_pos = {"q": int(sys.argv[3]), "r": int(sys.argv[4])}
        fleet_attack(target_id, target_pos)
    
    elif cmd == "test":
        # Quick test: attack nearby EDF
        accounts = load_fleet()
        if not accounts:
            print("No accounts!")
            sys.exit(1)
        
        # Get world state for first account
        acct = accounts[0]
        units, _, _ = get_world_state(acct["token"])
        our = [u for u in units if u.get("ownerId") == acct["userId"]]
        scout = next((u for u in our if u.get("type") == "Scout"), our[0] if our else None)
        edf = [u for u in units if u.get("ownerName") == "Earth Defense Force"]
        
        if scout and edf:
            closest = min(edf, key=lambda e: cube_dist(scout.get("position", {}), e.get("position", {})))
            print(f"Scout at {scout.get('position')}, closest EDF at {closest.get('position')} (dist={cube_dist(scout.get('position'), closest.get('position'))})")
            print(f"EDF HP: {closest.get('currentHp')}/{closest.get('maxHp')}")
            fleet_attack(closest["id"], closest.get("position"))
        else:
            print("No scout or EDF found")
    
    else:
        print(f"Unknown command: {cmd}")
