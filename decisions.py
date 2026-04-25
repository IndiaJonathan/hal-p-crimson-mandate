"""
Crimson Mandate Agent — Decision Engine (v2)
Rule-based strategy for mining, trading, and fleet management.
"""
import logging

logger = logging.getLogger("decisions")

MINERAL_SELL_THRESHOLDS = {
    "min_copper": 500, "min_iron": 500,
    "min_titanium": 200, "min_platinum": 100,
    "min_rhodium": 50, "min_palladium": 50,
    "min_iridium": 20, "min_darkmat": 10,
}

# Tier 1 mining laser (Mk1) unlocks uncommon minerals
# Tier 0 (Basic Mining Array) only handles COMMON minerals
# Asteroids near Earth tend to be common tier
COMMON_MINERAL_IDS = ["min_copper", "min_iron"]

# Preferred asteroids by tier
ASTEROID_MINERAL_TIER = {
    # tier 0: common only — Basic Mining Array works
    # tier 1: uncommon — requires Mining Laser Mk1 ($1)
    # tier 2: rare — requires Mining Laser Mk2 ($2)
    # tier 3: epic — requires Mining Laser Mk3 ($4)
    # tier 4: legendary — requires Mining Laser Mk4 ($6)
}


def parse_world_state(ws_payload: dict) -> dict:
    """Parse raw WS world state into simplified dict."""
    chunks = ws_payload.get("chunks", [])
    return {
        "chunks": chunks,
        "units": [u for c in chunks for u in c.get("units", [])],
        "planets": [p for c in chunks for p in c.get("planets", [])],
        "asteroids": [a for c in chunks for a in c.get("asteroids", [])],
        "stations": [s for c in chunks for s in c.get("stations", [])],
    }


def distance_hex(pos1: dict, pos2: dict) -> int:
    """Hex distance using cube coordinates."""
    def cube(q, r):
        x = q
        z = r
        y = -x - z
        return (x, y, z)
    c1 = cube(pos1.get("q", 0), pos1.get("r", 0))
    c2 = cube(pos2.get("q", 0), pos2.get("r", 0))
    return max(abs(c1[i] - c2[i]) for i in range(3))


def find_nearest_asteroid(unit_pos: dict, asteroids: list, max_tier: int = 0) -> dict:
    """
    Find nearest asteroid.
    max_tier=0 → only common-tier asteroids (Basic Mining Array compatible)
    """
    if not asteroids:
        return None
    # Filter by tier if known (asteroids with known common minerals)
    candidates = []
    for a in asteroids:
        if a.get("isDepleted"):
            continue
        # Only pick asteroids that are likely common-tier
        # All spawned asteroids in Core zone near Earth are typically common
        pos = a.get("position", {})
        if pos:
            candidates.append((distance_hex(unit_pos, pos), a))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def find_nearest_planet(unit_pos: dict, planets: list) -> dict:
    """Find nearest planet."""
    if not planets:
        return {"position": {"q": 0, "r": 0}}
    best, best_dist = None, float("inf")
    for p in planets:
        d = distance_hex(unit_pos, p.get("position", {}))
        if d < best_dist:
            best_dist = d
            best = p
    return best or {"position": {"q": 0, "r": 0}}


def decide_actions(state: dict, ws_state: dict) -> list:
    """
    Decide and return list of actions to execute this cycle.
    """
    actions = []
    token = state.get("session", {}).get("token", "")
    user_id = state["commander"]["userId"]
    units = state.get("units", [])
    minerals = state.get("minerals", {})
    balance = state.get("balance", {})
    owned = [u for u in units if u.get("ownerId") == user_id]

    scout = next((u for u in owned if u.get("type") == "Scout"), None)
    if not scout:
        scout = owned[0] if owned else None

    asteroids_in_world = ws_state.get("asteroids", [])
    planets_in_world = ws_state.get("planets", [])

    # ── Check if we have a Mining Laser (skip mining if not) ──
    mining_failures = state.get("mining_failures", 0)
    has_laser = state.get("has_mining_laser", False)

    # ── Action: Move toward asteroid if not adjacent ──
    mining = [u for u in owned if u.get("miningAsteroidId")]
    idle = [u for u in owned if not u.get("miningAsteroidId") and not u.get("dockedAtPlanetId")]

    # Only try mining if we have a laser OR failures are low
    can_mine = has_laser or mining_failures < 2

    if scout and not mining and asteroids_in_world and can_mine:
        target = find_nearest_asteroid(scout.get("position", {}), asteroids_in_world, max_tier=0)
        if target:
            tpos = target.get("position", {})
            dist = distance_hex(scout.get("position", {}), tpos)
            if dist <= 1:
                # Adjacent — mine
                actions.append({
                    "type": "mine_asteroid",
                    "payload": {"unitId": scout["id"], "asteroidId": target["id"]},
                    "ws": True
                })
            elif dist <= 20:
                # Move toward asteroid
                actions.append({
                    "type": "move_unit",
                    "payload": {"unitId": scout["id"], "targetHex": tpos},
                    "ws": True
                })
    elif scout and not mining and asteroids_in_world and not can_mine:
        logger.warning("Mining blocked: no Mining Laser detected. Waiting for unlock.")

    # ── Action: Sell minerals above threshold ──
    sell_order = ["min_darkmat", "min_iridium", "min_rhodium", "min_palladium",
                  "min_platinum", "min_titanium", "min_copper", "min_iron"]
    for mid in sell_order:
        amt = minerals.get(mid, {}).get("amount", 0)
        if amt >= MINERAL_SELL_THRESHOLDS.get(mid, 100):
            actions.append({"type": "sell", "payload": {"mineralTypeId": mid, "amount": amt}, "ws": False})
            break

    # ── Action: Contribute to research if ISD available ──
    isd = balance.get("isdBalance", 0)
    if isd >= 100:
        board = state.get("research_board", [])
        for item in board:
            if item.get("status") == "funding" and not item.get("isFullyFunded"):
                isd_funded = item.get("isdFunded", 0)
                isd_req = item.get("isdCostRequired", 0)
                remaining = isd_req - isd_funded
                if remaining > 0 and isd >= 50:
                    contrib = min(float(isd), float(remaining))
                    actions.append({
                        "type": "contribute_research",
                        "payload": {"boardId": item["id"], "isdAmount": contrib},
                        "ws": False
                    })
                    break

    return actions
