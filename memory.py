"""
Crimson Mandate Agent — Persistent State Memory
"""
import json
import os
from datetime import datetime, timezone

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_session():
    state = load_state()
    return state.get("session", {})


def get_token():
    return get_session().get("token", "")


def log_action(state, action: str, detail: str = "", result: str = "ok"):
    """Append to action log, keep last 100 entries."""
    log = state.get("actionLog", [])
    log.append({
        "time": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "detail": detail,
        "result": result
    })
    # Keep last 100
    state["actionLog"] = log[-100:]
    return state


def update_balance(state, balance: dict):
    state["balance"] = balance
    return state


def update_minerals(state, minerals: list):
    """Index minerals by typeId."""
    state["minerals"] = {m["mineralTypeId"]: m for m in minerals}
    return state


def update_ships(state, ships: list):
    state["ships"] = ships
    state["commander"]["shipCount"] = len(ships)
    return state


def update_units(state, units: list):
    state["units"] = units
    return state


def update_planets(state, planets: list):
    state["planets"] = planets
    return state


def update_asteroids(state, asteroids: list):
    """Index asteroids by id."""
    existing = state.get("asteroids", {})
    for a in asteroids:
        existing[a["id"]] = a
    state["asteroids"] = existing
    return state


def update_stations(state, stations: list):
    state["stations"] = stations
    return state


def set_world_joined(state):
    state["worldJoined"] = True
    return state


def set_starter_spawned(state):
    state["starterSpawned"] = True
    return state


def get_owned_units(state):
    user_id = state["commander"]["userId"]
    return [u for u in state.get("units", []) if u.get("ownerId") == user_id]


def get_mining_units(state):
    """Units with active mining assignments."""
    return [u for u in state.get("units", []) if u.get("miningAsteroidId")]


def assign_mining(state, unit_id: str, asteroid_id: str):
    assignments = state.get("miningAssignments", {})
    assignments[unit_id] = asteroid_id
    state["miningAssignments"] = assignments
    return state


def get_total_minerals(state):
    """Total mineral count in inventory."""
    minerals = state.get("minerals", {})
    return sum(m.get("amount", 0) for m in minerals.values())


def set_next_run(state, timestamp: str):
    state["nextRun"] = timestamp
    return state
