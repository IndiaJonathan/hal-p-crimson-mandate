#!/usr/bin/env python3
"""Debug API connectivity"""
import json, sys, os, requests

sys.path.insert(0, '/Users/jonathan/.openclaw/workspace/crimson-mandate-agent')

with open('/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/state.json') as f:
    state = json.load(f)
token = state["session"]["token"]
headers = {"Authorization": f"Bearer {token}"}

BASE = "https://crimsonmandate.com"

# Test basic connectivity
print("=== Testing API Connectivity ===")

# Test 1: Check session validity
r = requests.get(f"{BASE}/api/auth/session", headers=headers, timeout=10)
print(f"Session check: {r.status_code} | {r.text[:200]}")

# Test 2: Units
r2 = requests.get(f"{BASE}/api/units", headers=headers, timeout=10)
print(f"Units: {r2.status_code} | {r2.text[:200]}")

# Test 3: World state
r3 = requests.get(f"{BASE}/api/world/state", headers=headers, timeout=10)
print(f"World state: {r3.status_code} | {r3.text[:200]}")