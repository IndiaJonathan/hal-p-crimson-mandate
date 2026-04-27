#!/usr/bin/env python3
"""
Crimson Mandate — ISD grind executor.
Runs every 5 min, decides best action, reports to Discord.
"""
import json, sys, os, time, requests, websocket
sys.path.insert(0, os.path.dirname(__file__))
from runner import MMOClient
from memory import load_state

BASE = "https://crimsonmandate.com"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

def cube_dist(p1, p2):
    def cube(q, r): return (q, -q-r, r)
    c1 = cube(p1.get("q",0), p1.get("r",0))
    c2 = cube(p2.get("q",0), p2.get("r",0))
    return max(abs(c1[i]-c2[i]) for i in range(3))

def send(msg):
    if not DISCORD_WEBHOOK:
        print(msg)
        return
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=10)
    except: pass

def main():
    email = "halp@burk-dashboards.com"
    password = "Test1234!"
    
    client = MMOClient(email, password, BASE)
    client.login()
    client.join_world()
    client.sync_state()
    
    scout = client.get_owned_scout()
    if not scout:
        send("🤖 **HALP Crimson | No Scout — waiting for respawn.**")
        return
    
    scout_pos = scout.get("position", {})
    scout_hp  = scout.get("currentHp", 40)
    scout_id  = scout["id"]
    
    # Check world for EDF
    units = client.get_world_units()
    edf = [u for u in units if u.get("ownerName") == "Earth Defense Force"]
    fighters = [e for e in edf if "Fighter" in e.get("type","")]
    
    bal = client.get_balance()
    isd = bal.get("isdBalance", 0)
    credits = bal.get("credits", 0)
    
    action_taken = None
    result_msg = ""
    
    # If circuit breaker has fired, stay put — don't waste moves cycling home
    if state.get("mining_failures", 0) >= 5:
        send(
            f"**🤖 HALP Crimson Mandate**\n"
            f" ISD: `{isd}` | Credits: `{credits}`\n"
            f" Scout: `{scout_pos}` HP={scout_hp}/40\n"
            f" EDF Fighters visible: `{len(fighters)}`\n"
            f" → 💤 Circuit breaker ({state['mining_failures']} failures) — waiting for Mk1 Laser or iron/copper asteroid\n"
            f" → No valid action available"
        )
        return

    if fighters and scout_hp >= 20:
        # Attack nearest Fighter
        target = min(fighters, key=lambda e: cube_dist(scout_pos, e.get("position",{})))
        client.ws_attack(scout_id, target["id"], target.get("position",{}))
        action_taken = f"⚔️ Attacked {target['type']} at {target.get('position')} HP={target.get('currentHp')}"
        result_msg = f"Sent attack order"
    elif not fighters:
        # Move toward Earth (EDF patrol zone)
        client.ws_move(scout_id, {"q": 0, "r": 0})
        action_taken = f"🚀 Moved Scout to (0,0) — seeking EDF"
        result_msg = f"Moved toward patrol zone"
    else:
        action_taken = "⏳ Low HP — waiting for respawn"
        result_msg = f"Scout HP={scout_hp}, skipping combat"
    
    send(
        f"**🤖 HALP Crimson Mandate**\n"
        f" ISD: `{isd}` | Credits: `{credits}`\n"
        f" Scout: `{scout_pos}` HP={scout_hp}/40\n"
        f" EDF Fighters visible: `{len(fighters)}`\n"
        f" → {action_taken}\n"
        f" → {result_msg}"
    )

if __name__ == "__main__":
    main()
