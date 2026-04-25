#!/usr/bin/env python3
"""
Crimson Mandate Agent — Self-Improvement Runner
Analyzes past runs, identifies failures, makes targeted fixes.
"""
import json, os, sys, re, subprocess, datetime as dt

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(AGENT_DIR, "runner.log")
STATE_FILE = os.path.join(AGENT_DIR, "state.json")

def ts():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def read_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE) as f:
        return json.load(f)

def read_log():
    if not os.path.exists(LOG_FILE):
        return ""
    with open(LOG_FILE) as f:
        return f.read()

def analyze_resource_trend(state, log_text):
    balance = state.get("balance", {})
    isd = balance.get("isdBalance", 0)
    credits = balance.get("credits", 0)
    minerals = state.get("minerals", {})
    total_minerals = sum(m.get("amount", 0) for m in minerals.values())
    return f"ISD={isd}, Credits={credits}, Minerals={total_minerals}"

def analyze_failures(log_text):
    issues = []
    for line in log_text.split("\n"):
        if "error" in line.lower() or "traceback" in line.lower():
            issues.append(line.strip())
    return issues[:10]

def check_missing_mining_laser(state, log_text):
    """If mining keeps failing without a laser, flag it."""
    failures = state.get("mining_failures", 0)
    has_laser = state.get("has_mining_laser", False)
    if failures >= 3 and not has_laser:
        return "⚠️ Mining blocked — no Mining Laser Mk1 (costs 1000 ISD). Prioritize combat ISD grinding."
    return None

def check_stale_position(state):
    """If scout has been at the same position for many cycles, it may be stuck."""
    units = state.get("units", [])
    scout = next((u for u in units if "Scout" in u.get("type", "")), None)
    if not scout:
        return "⚠️ No Scout found — may have been destroyed and is respawning."
    return None

def decide_top_priority(state):
    """
    Returns (priority_label, action_description)
    """
    balance = state.get("balance", {})
    isd = balance.get("isdBalance", 0)
    has_laser = state.get("has_mining_laser", False)
    failures = state.get("mining_failures", 0)
    units = state.get("units", [])
    scout = next((u for u in units if "Scout" in u.get("type", "")), None)

    if not scout:
        return ("⏳ WAIT", "Scout destroyed — waiting for auto-respawn (~60s)")

    if isd >= 1000 and not has_laser:
        return ("🎯 BUY LASER", "1000 ISD reached — purchase Mining Laser Mk1 to unlock tier-1 mining")

    if isd >= 750:
        return ("💡 RESEARCH", "ISD available — contribute to research board (750 ISD Enhanced Sensor Array)")

    if not has_laser and failures < 3:
        # Still trying to mine without laser — switch to combat
        return ("⚔️ COMBAT", "Mining without laser is low-value — grind EDF Fighters for ISD")

    if has_laser:
        return ("⛏️ MINE", "Mining Laser active — mine tier-1 asteroids for minerals")

    return ("⚔️ COMBAT", "Grind EDF Fighters for ISD to unlock gear")

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("Crimson Mandate Agent — Self-Improvement Check")
    print(f"  {ts()}")
    print("="*60)

    state = read_state()
    log_text = read_log()

    print(f"\n📊 Resources: {analyze_resource_trend(state, log_text)}")

    laser_warning = check_missing_mining_laser(state, log_text)
    if laser_warning:
        print(f"\n{laser_warning}")

    scout_warning = check_stale_position(state)
    if scout_warning:
        print(f"\n{scout_warning}")

    priority, action = decide_top_priority(state)
    print(f"\n🎯 Top Priority: {priority}")
    print(f"   Action: {action}")

    issues = analyze_failures(log_text)
    if issues:
        print(f"\n🔍 Recent issues ({len(issues)}):")
        for issue in issues[:5]:
            print(f"   {issue[:120]}")

    print(f"\n{'='*60}\n")
