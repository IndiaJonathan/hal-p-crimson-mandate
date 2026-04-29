#!/usr/bin/env python3
"""Mission: Break mining deadlock — scout Mars + expand halp2 coverage"""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from runner import MMOClient
from memory import load_state

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

def hex_distance(a, b):
    q1, r1 = a.get('q', 0), a.get('r', 0)
    q2, r2 = b.get('q', 0), b.get('r', 0)
    return max(abs(q1-q2), abs(r1-r2), abs((q1+r1)-(q2+r2)))

def wait_for_move(c, label):
    events = c.wait_for("mmo_unit_moved", timeout=15)
    if events:
        print(f"  ✓ {label}: mmo_unit_moved confirmed")
        return True
    print(f"  ✗ {label}: NO mmo_unit_moved in 15s")
    return False

# ── HALP: Auth + Move toward Mars + Scout ────────────────────────────────────
print("=" * 60)
print("PHASE 1: HALP Scout → Mars")
print("=" * 60)

halp_state = load_state()
halp_token = halp_state.get("session", {}).get("token", "")
halp_session = halp_state.get("session", {}).get("sessionId", "")

if not halp_token:
    print("ERROR: No halp token. Run auth.py first.")
    sys.exit(1)

c = MMOClient(halp_token, halp_session)
c.start()
if not c.wait_for_auth(timeout=10):
    print("ERROR: halp WS auth failed")
    c.stop()
    sys.exit(1)
print("  ✓ halp WS authenticated")

ws = c.get_world_state(timeout=15)
c.stop()

if not ws:
    print("ERROR: No world state received")
    sys.exit(1)

units = ws.get("units", [])
asteroids = ws.get("asteroids", [])
print(f"\nWorld state: {len(units)} units, {len(asteroids)} asteroids")

# Find halp scout
halp_scout = None
for u in units:
    owner = u.get("ownerId", "")
    if "halp" in str(u.get("ownerName", "")).lower() or u.get("type") == "Scout":
        # check ownership
        if owner == halp_state["commander"]["userId"]:
            halp_scout = u
            break

# Also search by unitId
if not halp_scout:
    for u in units:
        if "scout" in u.get("id", "").lower():
            halp_scout = u
            break

if halp_scout:
    print(f"\nHALP Scout found: {halp_scout['id']}")
    print(f"  Position: ({halp_scout['position'].get('q',0)}, {halp_scout['position'].get('r',0)})")
    print(f"  Type: {halp_scout.get('type')}")
    print(f"  Owner: {halp_scout.get('ownerName')}")
    print(f"  OwnerId: {halp_scout.get('ownerId')}")
    scout_id = halp_scout['id']
else:
    print("WARNING: halp scout not found by ownership. Using first Scout found.")
    for u in units:
        if u.get("type") == "Scout":
            halp_scout = u
            scout_id = u['id']
            print(f"  Fallback scout: {scout_id} at ({u['position'].get('q')},{u['position'].get('r')})")
            break

# Move halp scout toward Mars (12, -5)
mars = {"q": 12, "r": -5}
print(f"\n→ Moving HALP scout toward Mars {mars}...")

c2 = MMOClient(halp_token, halp_session)
c2.start()
if not c2.wait_for_auth(timeout=8):
    c2.stop()
    sys.exit(1)

# Also get fresh world state for position
_ = c2.get_world_state(timeout=10)

c2._send({"type": "mmo_move_unit", "payload": {
    "unitId": scout_id,
    "targetHex": mars
}})
wait_for_move(c2, "HALP→Mars")
c2.stop()

# Re-fetch world state after move
print("\nFetching post-move world state...")
c3 = MMOClient(halp_token, halp_session)
c3.start()
if c3.wait_for_auth(timeout=8):
    ws2 = c3.get_world_state(timeout=15)
    if ws2:
        units2 = ws2.get("units", [])
        asteroids2 = ws2.get("asteroids", [])
        planets2 = ws2.get("planets", [])
        
        # Find HALP scout new position
        for u in units2:
            if u.get("id") == scout_id:
                print(f"\nHALP Scout NEW position: ({u['position'].get('q')}, {u['position'].get('r')})")
                break
        
        print(f"\n{'='*60}")
        print("ASTEROID SURVEY (post-move)")
        print(f"{'='*60}")
        print(f"Total asteroids visible: {len(asteroids2)}")
        
        mars = {"q": 12, "r": -5}
        iron_near_mars = []
        copper_near_mars = []
        
        for a in asteroids2:
            pos = a.get("position", {})
            dist = hex_distance(pos, mars)
            minerals = a.get("mineralComposition", {})
            a_info = {
                "id": a.get("id"),
                "position": pos,
                "distance_to_mars": dist,
                "minerals": minerals,
                "type": a.get("type"),
                "ownerName": a.get("ownerName", "unclaimed")
            }
            print(f"\n  Asteroid: {a.get('id')}")
            print(f"    Position: ({pos.get('q')}, {pos.get('r')}) | Dist to Mars: {dist}")
            print(f"    Type: {a.get('type')} | Owner: {a_info['ownerName']}")
            print(f"    Minerals: {json.dumps(minerals)}")
            
            if dist <= 5:
                # Check for iron/copper
                for m, v in minerals.items():
                    if v and v > 0:
                        m_lower = m.lower()
                        if "iron" in m_lower:
                            iron_near_mars.append(a_info)
                        elif "copper" in m_lower:
                            copper_near_mars.append(a_info)
        
        print(f"\n{'='*60}")
        print("EDF FIGHTERS")
        print(f"{'='*60}")
        edf = [u for u in units2 if "earth defense" in u.get("ownerName", "").lower() or u.get("ownerName") == "Earth Defense Force"]
        if edf:
            for e in edf:
                pos = e.get("position", {})
                dist_mars = hex_distance(pos, mars)
                print(f"\n  EDF Unit: {e.get('id')}")
                print(f"    Type: {e.get('type')} | Pos: ({pos.get('q')},{pos.get('r')})")
                print(f"    Dist to Mars: {dist_mars}")
        else:
            print("  No EDF fighters visible.")
        
        print(f"\n{'='*60}")
        print(f"NEAR-MARS SUMMARY (≤5 hexes)")
        print(f"{'='*60}")
        print(f"  Iron asteroids near Mars: {len(iron_near_mars)}")
        for a in iron_near_mars:
            print(f"    - {a['id']} at ({a['position'].get('q')},{a['position'].get('r')}) minerals={json.dumps(a['minerals'])}")
        print(f"  Copper asteroids near Mars: {len(copper_near_mars)}")
        for a in copper_near_mars:
            print(f"    - {a['id']} at ({a['position'].get('q')},{a['position'].get('r')}) minerals={json.dumps(a['minerals'])}")
        
        # Save findings
        findings = {
            "iron_near_mars": iron_near_mars,
            "copper_near_mars": copper_near_mars,
            "edf_units": [{"id": e.get("id"), "type": e.get("type"), "position": e.get("position"), "dist_to_mars": hex_distance(e.get("position", {}), mars)} for e in edf],
            "total_asteroids": len(asteroids2),
            "mars_position": mars
        }
        with open(os.path.join(AGENT_DIR, "mission_findings.json"), "w") as f:
            json.dump(findings, f, indent=2, default=str)
        
c3.stop()

# ── HALP2: Auth + Move toward (-30, 15) ──────────────────────────────────────
print(f"\n{'='*60}")
print("PHASE 2: HALP2 Scout → (-30, 15)")
print(f"{'='*60}")

# Re-auth halp2
import subprocess
result = subprocess.run(
    ["/bin/bash", "-c", "cd /Users/jonathan/.openclaw/workspace/crimson-mandate-agent && source venv/bin/activate && python3 auth.py halp2@burk-dashboards.com Test1234!"],
    capture_output=True, text=True, timeout=30
)
print(result.stdout)
if result.returncode != 0:
    print("halp2 auth stderr:", result.stderr[:500])

time.sleep(2)

halp2_state = load_state()
halp2_token = halp2_state.get("session", {}).get("token", "")
halp2_session = halp2_state.get("session", {}).get("sessionId", "")

print(f"halp2 token: {halp2_token[:30]}...")
print(f"halp2 session: {halp2_session}")

# Get halp2 units via WS
c4 = MMOClient(halp2_token, halp2_session)
c4.start()
if not c4.wait_for_auth(timeout=10):
    print("ERROR: halp2 WS auth failed")
    c4.stop()
else:
    ws_halp2 = c4.get_world_state(timeout=15)
    if ws_halp2:
        halp2_units = ws_halp2.get("units", [])
        halp2_user = halp2_state["commander"]["userId"]
        print(f"\nHALP2 world state: {len(halp2_units)} units")
        
        halp2_scout = None
        for u in halp2_units:
            print(f"  Unit: {u.get('id')} | type={u.get('type')} | owner={u.get('ownerName')} | pos=({u.get('position',{}).get('q')},{u.get('position',{}).get('r')})")
            # Match halp2 by ownerName or by id containing halp2
            owner = u.get("ownerName", "")
            if "halp2" in owner.lower():
                halp2_scout = u
        
        if not halp2_scout:
            # Try by id
            for u in halp2_units:
                if "scout" in u.get("id", "").lower():
                    halp2_scout = u
        
        if halp2_scout:
            halp2_scout_id = halp2_scout["id"]
            print(f"\nHALP2 Scout: {halp2_scout_id}")
            print(f"  Current position: ({halp2_scout['position'].get('q')}, {halp2_scout['position'].get('r')})")
            
            target = {"q": -30, "r": 15}
            print(f"  → Moving to {target}...")
            
            c4._send({"type": "mmo_move_unit", "payload": {
                "unitId": halp2_scout_id,
                "targetHex": target
            }})
            wait_for_move(c4, "HALP2→(-30,15)")
        else:
            print("WARNING: halp2 scout not found in world state!")
            # Just use the scout ID we know about
            print("  Trying with halp2 scout ID from state file...")
            # Look for any scout
            for u in halp2_units:
                if u.get("type") == "Scout":
                    halp2_scout_id = u["id"]
                    target = {"q": -30, "r": 15}
                    c4._send({"type": "mmo_move_unit", "payload": {
                        "unitId": halp2_scout_id,
                        "targetHex": target
                    }})
                    wait_for_move(c4, "HALP2→(-30,15)")
                    break
    c4.stop()

print("\n" + "="*60)
print("MISSION COMPLETE")
print("="*60)
