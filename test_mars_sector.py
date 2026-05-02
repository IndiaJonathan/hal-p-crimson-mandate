#!/usr/bin/env python3
"""Probe Mars sector (11,-5) and (12,-5) for asteroid visibility"""
import json, sys
sys.path.insert(0, '/Users/jonathan/.openclaw/workspace/crimson-mandate-agent')
from mmo_client import MMOClient

client = MMOClient()
client.load_state()

# Send sensor sweep targeting Mars sector coordinates
# Use the move_to command to set destination, then probe
probe_actions = []

# Action 1: Move scout to (11,-5)
probe_actions.append({
    "type": "game_command",
    "command": "move_to",
    "entity_id": client.state["scout_id"],
    "x": 11,
    "y": -5
})

# Action 2: Immediately probe world state
probe_actions.append({
    "type": "mission_scout",
    "account": "halp"
})

# Send batch
results = []
for action in probe_actions:
    r = client.send(action)
    results.append({"sent": action, "received": r})
    import time; time.sleep(2)

print(json.dumps(results, indent=2))