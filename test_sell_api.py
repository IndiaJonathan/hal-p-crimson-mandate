#!/usr/bin/env python3
"""Test component sell API — no assumptions, just try it."""
import json, requests

BASE = "https://crimsonmandate.com"

# Load halp token
with open("state.json") as f:
    state = json.load(f)
token = state["session"]["token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

print("=== Testing component sell endpoints ===\n")

# Check inventory first
print("[1] GET /api/inventory")
try:
    r = requests.get(f"{BASE}/api/inventory", headers=headers, timeout=10)
    print(f"    Status: {r.status_code}")
    print(f"    Body: {r.text[:500]}")
except Exception as e:
    print(f"    Error: {e}")

print()

# Try selling wpn_beam_laser_light (64 units)
print("[2] POST /api/inventory/sell")
try:
    r = requests.post(f"{BASE}/api/inventory/sell", 
        headers=headers,
        json={"componentName": "wpn_beam_laser_light", "quantity": 1},
        timeout=10)
    print(f"    Status: {r.status_code}")
    print(f"    Body: {r.text[:500]}")
except Exception as e:
    print(f"    Error: {e}")

print()

# Try alternate sell endpoint
print("[3] POST /api/components/sell")
try:
    r = requests.post(f"{BASE}/api/components/sell",
        headers=headers,
        json={"componentName": "wpn_beam_laser_light", "quantity": 1},
        timeout=10)
    print(f"    Status: {r.status_code}")
    print(f"    Body: {r.text[:500]}")
except Exception as e:
    print(f"    Error: {e}")

print()

# Try market endpoint
print("[4] GET /api/market")
try:
    r = requests.get(f"{BASE}/api/market", headers=headers, timeout=10)
    print(f"    Status: {r.status_code}")
    print(f"    Body: {r.text[:500]}")
except Exception as e:
    print(f"    Error: {e}")

print()

# Try shop endpoint
print("[5] GET /api/shop")
try:
    r = requests.get(f"{BASE}/api/shop", headers=headers, timeout=10)
    print(f"    Status: {r.status_code}")
    print(f"    Body: {r.text[:500]}")
except Exception as e:
    print(f"    Error: {e}")

print()

# Try store endpoint
print("[6] GET /api/store")
try:
    r = requests.get(f"{BASE}/api/store", headers=headers, timeout=10)
    print(f"    Status: {r.status_code}")
    print(f"    Body: {r.text[:500]}")
except Exception as e:
    print(f"    Error: {e}")

print()

# Try trading post
print("[7] GET /api/trade")
try:
    r = requests.get(f"{BASE}/api/trade", headers=headers, timeout=10)
    print(f"    Status: {r.status_code}")
    print(f"    Body: {r.text[:500]}")
except Exception as e:
    print(f"    Error: {e}")

print()

# Try component list endpoint
print("[8] GET /api/components")
try:
    r = requests.get(f"{BASE}/api/components", headers=headers, timeout=10)
    print(f"    Status: {r.status_code}")
    print(f"    Body: {r.text[:500]}")
except Exception as e:
    print(f"    Error: {e}")

print()

# Try ISDTools or isd/sell
print("[9] POST /api/isd/sell")
try:
    r = requests.post(f"{BASE}/api/isd/sell",
        headers=headers,
        json={"amount": 100},
        timeout=10)
    print(f"    Status: {r.status_code}")
    print(f"    Body: {r.text[:500]}")
except Exception as e:
    print(f"    Error: {e}")

print()

# Try withdraw ISD
print("[10] POST /api/isd/withdraw")
try:
    r = requests.post(f"{BASE}/api/isd/withdraw",
        headers=headers,
        json={"amount": 100},
        timeout=10)
    print(f"    Status: {r.status_code}")
    print(f"    Body: {r.text[:500]}")
except Exception as e:
    print(f"    Error: {e}")

print()

# Try buy laser for components
print("[11] POST /api/ships/buy")
try:
    r = requests.post(f"{BASE}/api/ships/buy",
        headers=headers,
        json={"shipType": "Fighter", "isdAmount": 500},
        timeout=10)
    print(f"    Status: {r.status_code}")
    print(f"    Body: {r.text[:500]}")
except Exception as e:
    print(f"    Error: {e}")

print("\n=== Done ===")