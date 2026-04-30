#!/usr/bin/env python3
"""Explore available API endpoints"""
import json, requests

with open('/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/state.json') as f:
    state = json.load(f)
token = state["session"]["token"]
headers = {"Authorization": f"Bearer {token}"}

BASE = "https://crimsonmandate.com"

endpoints = [
    "/api/auth/session",
    "/api/game/status",
    "/api/game/state",
    "/api/player",
    "/api/player/status",
    "/api/units",
    "/api/units/list",
    "/api/world/state",
    "/api/world",
    "/api/asteroids",
    "/api/sectors",
    "/api/map",
    "/api/commander",
    "/api/commander/status",
    "/api/resources",
]

for ep in endpoints:
    try:
        r = requests.get(f"{BASE}{ep}", headers=headers, timeout=5)
        print(f"{ep}: {r.status_code} | {r.text[:150]}")
    except Exception as e:
        print(f"{ep}: ERROR {e}")