#!/usr/bin/env python3
"""
Crimson Mandate Agent — Self-Improvement Runner
Analyzes past runs, identifies failures, makes targeted fixes.
Commits improvements to GitHub.
"""
import json, os, sys, re, subprocess, datetime

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(AGENT_DIR, "runner.log")
STATE_FILE = os.path.join(AGENT_DIR, "state.json")
IMPROVE_LOG = os.path.join(AGENT_DIR, "improvement_log.md")

def log(msg):
    print(f"[IMPROVE] {msg}")

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

def git_commit(msg):
    try:
        subprocess.run(["git", "add", "-A"], cwd=AGENT_DIR, capture_output=True)
        result = subprocess.run(["git", "commit", "-m", msg], cwd=AGENT_DIR, capture_output=True, text=True)
        if result.returncode == 0:
            subprocess.run(["git", "push", "origin", "main"], cwd=AGENT_DIR, capture_output=True, text=True)
            return True
        return False
    except Exception as e:
        log(f"Git error: {e}")
        return False

def analyze_failures(log_text: str) -> list:
    """Find patterns that need fixing."""
    issues = []

    # No resource growth check
    if "no world state" in log_text.lower():
        issues.append({"severity": "HIGH", "issue": "WS world state not received", "fix": "Check WS connection + auth"})
    if "auth timeout" in log_text.lower():
        issues.append({"severity": "HIGH", "issue": "WS auth timeout", "fix": "Token may be expired — run auth.py"})
    if "INVALID_TOKEN" in log_text:
        issues.append({"severity": "HIGH", "issue": "Token invalid", "fix": "Re-authenticate with auth.py"})
    if "requires mining laser" in log_text.lower() or "cannot extract" in log_text.lower() or "higher-tier mining" in log_text.lower():
        issues.append({"severity": "HIGH", "issue": "Mining blocked — Basic Mining Array can't handle asteroid tier", "fix": "STOP mining attempts until Mining Laser Mk1 acquired"})
    if "error" in log_text.lower() and "server error" in log_text.lower():
        # Extract the last error
        errors = re.findall(r"error.*?[{}\":a-zA-Z0-9_\s]+", log_text, re.I)
        if errors:
            issues.append({"severity": "LOW", "issue": errors[-1][:100], "fix": "Monitor"})

    return issues

def analyze_resource_trend(state: dict, log_text: str) -> str:
    """Check if resources are growing."""
    balance = state.get("balance", {})
    isd = balance.get("isdBalance", 0)
    credits = balance.get("credits", 0)
    minerals = state.get("minerals", {})

    total_minerals = sum(m.get("amount", 0) for m in minerals.values())

    # Count successful actions from log
    sells = log_text.count('"sell"') + log_text.count("sell")
    combat_wins = log_text.count("mmo_unit_destroyed_notification")
    mining_yields = log_text.count("mmo_mine_result")
    mining_fails = log_text.count("cannot extract") + log_text.count("higher-tier") + log_text.count("requires mining")

    trend = f"ISD={isd} credits={credits} minerals={total_minerals}"
    trend += f" | sells={sells} combat_wins={combat_wins} mining={mining_yields}"

    if isd > 0 or total_minerals > 0 or combat_wins > 0:
        return trend + " ✅ Growing"
    return trend + " ⚠️ Stalled"

def check_token_valid() -> bool:
    """Check if current token is still valid via a quick REST call."""
    state = read_state()
    token = state.get("session", {}).get("token", "")
    if not token:
        return False
    try:
        import requests
        resp = requests.get("https://crimsonmandate.com/api/profile/me",
                          headers={"Authorization": f"Bearer {token}"}, timeout=5)
        return resp.status_code == 200
    except:
        return False

def run():
    print("═"*60)
    print("Crimson Mandate Agent — Self-Improvement Check")
    print("═"*60)

    state = read_state()
    log_text = read_log()
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Resource check
    trend = analyze_resource_trend(state, log_text)
    print(f"\n📊 Resource Trend: {trend}")

    # Failure analysis
    issues = analyze_failures(log_text)
    if issues:
        print(f"\n🔍 Issues found ({len(issues)}):")
        for issue in issues:
            print(f"  [{issue['severity']}] {issue['issue']}")
            print(f"      Fix: {issue['fix']}")
    else:
        print(f"\n✅ No issues detected")

    # Token validity
    token_ok = check_token_valid()
    print(f"\n🔑 Token valid: {'✅' if token_ok else '❌ — run auth.py'}")

    # Log summary
    summary = f"""
## Self-Improve — {ts}

**Resource Trend:** {trend}
**Token:** {'✅ Valid' if token_ok else '❌ Expired'}

"""
    if issues:
        summary += "**Issues:**\n"
        for issue in issues:
            summary += f"- [{issue['severity']}] {issue['issue']} → {issue['fix']}\n"
    else:
        summary += "**Status:** No issues detected.\n"

    # Append to improvement log
    with open(IMPROVE_LOG, "a") as f:
        f.write(summary)

    # Git commit if there are meaningful changes
    try:
        result = subprocess.run(["git", "status", "--porcelain"], cwd=AGENT_DIR, capture_output=True, text=True)
        if result.stdout.strip():
            git_commit(f"Improve: {trend[:60]} | {ts}")
            print(f"\n📦 Changes committed + pushed")
    except Exception as e:
        print(f"\n⚠️ Git commit failed: {e}")

    print("\nDone.\n")

if __name__ == "__main__":
    run()
