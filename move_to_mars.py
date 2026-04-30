#!/usr/bin/env python3
"""Move HALP's actual scout to Mars and scan for asteroids"""
import sys, os, time, json
sys.path.insert(0, '/Users/jonathan/.openclaw/workspace/crimson-mandate-agent')

from runner import MMOClient
from memory import load_state

AGENT_DIR = '/Users/jonathan/.openclaw/workspace/crimson-mandate-agent'

HALP_SCOUT_ID = "unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_respawn_f696459e"

def hex_distance(a, b):
    q1, r1 = a.get('q', 0), a.get('r', 0)
    q2, r2 = b.get('q', 0), b.get('r', 0)
    return max(abs(q1-q2), abs(r1-r2), abs((q1+r1)-(q2+r2)))

def wait_for_move(c, label):
    events = c.wait_for("mmo_unit_moved", timeout=15)
    if events:
        print(f"  ✓ {label}: moved")
        return True
    print(f"  ✗ {label}: no move confirmation")
    return False

print("=" * 60)
print("HALP Scout (respawn) → Mars (12,-5)")
print("=" * 60)

halp_state = load_state()
token = halp_state.get("session", {}).get("token", "")
session_id = halp_state.get("session", {}).get("sessionId", "")

if not token:
    print("ERROR: No token. Run auth.py first.")
    sys.exit(1)

# Get fresh world state to find HALP's actual position
c = MMOClient(token, session_id)
c.start()
if not c.wait_for_auth(timeout=10):
    print("WS auth failed")
    c.stop()
    sys.exit(1)

ws = c.get_world_state(timeout=15)
c.stop()

units = ws.get("units", [])
asteroids = ws.get("asteroids", [])
planets = ws.get("planets", [])

# Find HALP's specific respawn scout directly
halp_scout = None
for u in units:
    if u.get("id") == HALP_SCOUT_ID:
        halp_scout = u
        break

if not halp_scout:
    print(f"ERROR: HALP scout {HALP_SCOUT_ID} not found!")
    print("Available scouts:")
    for u in units:
        if "scout" in u.get("type", "").lower():
            print(f"  {u.get('id')} owner={u.get('ownerName')} pos=({u.get('position',{}).get('q')},{u.get('position',{}).get('r')})")
    sys.exit(1)

scout_id = halp_scout["id"]
current_pos = halp_scout.get("position", {})
mars = {"q": 12, "r": -5}
print(f"HALP Scout: {scout_id}")
print(f"  Position: ({current_pos.get('q')},{current_pos.get('r')})")
print(f"  Type: {halp_scout.get('type')} | Owner: {halp_scout.get('ownerName')}")
print(f"  Target: Mars {mars} — distance {hex_distance(current_pos, mars)}")

# Determine next step
cq, cr = current_pos.get('q', 0), current_pos.get('r', 0)
mq, mr = mars['q'], mars['r']
if cq < mq:
    step_q = cq + 1
else:
    step_q = cq
if cr < mr:
    step_r = cr + 1
elif cr > mr:
    step_r = cr - 1
else:
    step_r = cr

step = {"q": step_q, "r": step_r}
print(f"\n→ Moving one step to {step} (toward Mars)...")

c2 = MMOClient(token, session_id)
c2.start()
if not c2.wait_for_auth(timeout=8):
    c2.stop()
    sys.exit(1)

_ = c2.get_world_state(timeout=10)
c2._send({"type": "mmo_move_unit", "payload": {
    "unitId": scout_id,
    "targetHex": step
}})
wait_for_move(c2, f"Scout→{step}")
c2.stop()

time.sleep(2)

# Full post-move world state
print("\nFetching full world state...")
c3 = MMOClient(token, session_id)
c3.start()
if c3.wait_for_auth(timeout=8):
    ws2 = c3.get_world_state(timeout=15)
    if ws2:
        units2 = ws2.get("units", [])
        asteroids2 = ws2.get("asteroids", [])
        planets2 = ws2.get("planets", [])
        
        new_pos = None
        for u in units2:
            if u.get("id") == scout_id:
                new_pos = u.get("position", {})
                print(f"\nHALP Scout NOW at: ({new_pos.get('q')},{new_pos.get('r')})")
                print(f"  Distance to Mars (12,-5): {hex_distance(new_pos, mars)}")
                break
        
        print(f"\n{'='*60}")
        print(f"WORLD STATE SUMMARY")
        print(f"{'='*60}")
        print(f"  Units: {len(units2)}")
        print(f"  Asteroids: {len(asteroids2)}")
        print(f"  Planets: {len(planets2)}")
        
        # Show planets near Mars (within 10 hexes)
        print(f"\n  Planets near Mars (12,-5):")
        for p in planets2:
            ppos = p.get('position', {})
            dist = hex_distance(ppos, mars)
            if dist <= 10:
                print(f"    {p.get('name','?')} pos=({ppos.get('q')},{ppos.get('r')}) dist={dist}")
        
        print(f"\n{'='*60}")
        print(f"ASTEROID SURVEY")
        print(f"{'='*60}")
        if not asteroids2:
            print("  No asteroids visible in world state.")
        else:
            print(f"  Total: {len(asteroids2)}")
            # Show by distance from Mars
            by_dist = sorted(asteroids2, key=lambda a: hex_distance(a.get('position', {}), mars))
            for a in by_dist[:20]:
                pos = a.get("position", {})
                dist = hex_distance(pos, mars)
                minerals = a.get("mineralComposition", {})
                owner = a.get("ownerName", "unclaimed")
                print(f"\n  Asteroid: {a.get('id')}")
                print(f"    Pos: ({pos.get('q')},{pos.get('r')}) | Dist to Mars: {dist}")
                print(f"    Type: {a.get('type')} | Variant: {a.get('variant')} | Owner: {owner}")
                print(f"    Minerals: {json.dumps(minerals)}")
        
        # EDF check
        edf = [u for u in units2 if u.get("ownerName") == "Earth Defense Force"]
        print(f"\n  EDF fighters visible: {len(edf)}")
        for e in edf[:5]:
            epos = e.get("position", {})
            print(f"    {e.get('id')} type={e.get('type')} pos=({epos.get('q')},{epos.get('r')})")
        
        # Save findings
        findings = {
            "scout_id": scout_id,
            "scout_position_before": current_pos,
            "scout_position_after": new_pos,
            "total_asteroids": len(asteroids2),
            "edf_count": len(edf),
            "mars": mars
        }
        with open(os.path.join(AGENT_DIR, "mars_scout_findings.json"), "w") as f:
            json.dump(findings, f, indent=2)
        print(f"\n  Findings saved.")

c3.stop()
print("\nDone.")