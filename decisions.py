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
    candidates = []
    for a in asteroids:
        if a.get("isDepleted"):
            continue
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

    # Use WS asteroids if available; fall back to REST-synced state asteroids
    asteroids_in_world = ws_state.get("asteroids", []) or state.get("asteroids", {}).values()
    if isinstance(asteroids_in_world, dict):
        asteroids_in_world = list(asteroids_in_world.values())
    planets_in_world = ws_state.get("planets", []) or state.get("planets", [])

    mining_failures = state.get("mining_failures", 0)
    has_laser = state.get("has_mining_laser", False)
    mining_blocked = (mining_failures >= 5)

    mining = [u for u in owned if u.get("miningAsteroidId")]
    idle = [u for u in owned if not u.get("miningAsteroidId") and not u.get("dockedAtPlanetId")]

    pending = state.get("_pending_minerals", {})
    # Merge REST minerals + pending WS yields; handle empty REST minerals gracefully
    if minerals:
        all_minerals = {k: {"amount": v.get("amount", 0) + pending.get(k, 0)} for k, v in minerals.items()}
    else:
        # REST sync cleared minerals (or none yet) — use pending only
        all_minerals = {k: {"amount": v} for k, v in pending.items()}

    # ── Tier-0 asteroids: miningLevel=0 AND no required component ──
    tier0_asteroids = [
        a for a in asteroids_in_world
        if not a.get("isDepleted")
        and a.get("miningLevel", 0) == 0
        and a.get("requiredComponentId") is None
    ]

    # Fall back to any asteroid with no required component if none have miningLevel=0
    if not tier0_asteroids:
        tier0_asteroids = [
            a for a in asteroids_in_world
            if not a.get("isDepleted")
            and a.get("requiredComponentId") is None
        ]

    # ── Mine or move to asteroid ──
    if scout and not mining and asteroids_in_world and not mining_blocked:
        target = find_nearest_asteroid(scout.get("position", {}), tier0_asteroids, max_tier=0)
        if target:
            tpos = target.get("position", {})
            dist = distance_hex(scout.get("position", {}), tpos)
            if dist <= 1:
                actions.append({
                    "type": "mine_asteroid",
                    "payload": {"unitId": scout["id"], "asteroidId": target["id"]},
                    "ws": True
                })
            elif dist <= 20:
                actions.append({
                    "type": "move_unit",
                    "payload": {"unitId": scout["id"], "targetHex": tpos},
                    "ws": True
                })
        elif not tier0_asteroids:
            # Prevent moving toward Earth (0,0) when already on/near an asteroid
            scout_pos = scout.get("position", {})
            if scout_pos and distance_hex(scout_pos, {"q": 0, "r": 0}) <= 20:
                logger.warning("Scout near asteroid but none in range — staying put.")
            else:
                logger.warning("No mineable asteroids (Basic Mining Array compatible).")

    elif mining_blocked:
        logger.warning("Mining blocked: 5+ failures. Waiting for Mk1 Mining Laser.")

    # ── Sell minerals above threshold ──
    sell_order = ["min_darkmat", "min_iridium", "min_rhodium", "min_palladium",
                  "min_platinum", "min_titanium", "min_copper", "min_iron"]
    for mid in sell_order:
        amt = all_minerals.get(mid, {}).get("amount", 0)
        if amt >= MINERAL_SELL_THRESHOLDS.get(mid, 100):
            actions.append({"type": "sell", "payload": {"mineralTypeId": mid, "amount": amt}, "ws": False})
            break

    # ── Contribute to research if ISD available ──
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
