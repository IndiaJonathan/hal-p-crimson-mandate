# Crimson Mandate GSD — STATE.md
# HAL-P self-executes. No token budget. No subagent chains. Direct action.

## Mission
Break the mining deadlock: ISD 490 → 1000 → buy Mk1 Laser → resume mining.

## Current State
- **ISD:** 490
- **Laser:** Mk0 (no Mk1)
- **Mining failures:** 70 (circuit breaker armed)
- **Scout position:** (2,0) — UPDATED from (28,-31) after respawn
- **halp2 position:** (1,0) → now moving toward (-30,15)
- **Operators:** Running (operator + golden_hunter_multi.py)
- **Strategy cron:** Running every 5 min (b56d3ffd)
- **Research:** Disabled (was draining ISD)
- **Token valid until:** 2026-05-02

## What's Been Tried
- Golden asteroid hunting → only path, no spawns yet
- Combat with EDF → scout dies in 1 round, not viable
- Research contributions → was ISD drain, now disabled
- All REST API endpoints → 404 or credits-only, no ISD path

## Current Objective
Find ANY path to 1000 ISD without buying laser with real money.

## Latest Test Results (2026-04-28 22:27 CDT)
### Mars Scout Mission
- **HALP Scout ID:** unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_respawn_f696459e
- **HALP Scout position:** (2,0) after one move toward Mars
- **HALP Scout moved toward:** Mars (12,-5) — 1 step confirmed
- **Mars target:** (12,-5) — still ~16+ hexes away, needs multiple moves
- **World state asteroids:** 0 (across all 4 visible chunks)
- **EDF fighters visible:** 0 (none near current position)
- **Asteroid data:** No asteroids in any of the 4 visible world chunks
- **fogOfWar entries:** 169 (fog of war is active/historical)
- **currentVision entries:** 37 (visible now)
- **Note:** Scout may need to move much closer to Mars sector to find asteroid fields
- **HALP2 Scout ID:** unit_scout_4cfa6a2a-11e6-439b-afca-7a60890694c1_1
- **HALP2 moved to:** (-30,15) — confirmed mmo_unit_moved
- **HALP2 starting position:** (1,0)

### Key Observations
1. **No asteroids visible** from current scout position (2,0)
   - World state chunks all show 0 asteroids
   - Possible: asteroids are only visible when within direct sensor range
   - Possible: fog of war hides them until scout is closer
2. **No EDF fighters** visible from current position
3. **HALP scout is far from Mars** — needs ~16+ moves to reach (12,-5)
   - Scout moved from (1,0) to (2,0) in one move cycle
4. **HALP2** is now en route to (-30,15) to expand coverage

### Next Scout Actions
1. **Continue moving HALP scout toward Mars (12,-5)** — need multiple cycles
2. **After each move, re-check for asteroid visibility** — they may only appear when in range
3. **HALP2 coverage zone** — now exploring toward (-30,15)
4. **Consider sending HALP scout to different zone** if Mars sector shows no asteroids after multiple moves

## Next Actions (Priority Order)
1. Move HALP scout toward Mars (12,-5) — needs ~16 more moves (run multiple cycles)
2. After each move: re-check WS chunks for asteroids
3. Move halp2 scout to explore different sector
4. Test Sensor Sweep ability — might reveal EDF targets outside normal sensor range
5. Check if component selling (Beam Lasers) yields anything useful

## Lock
Lock file: /tmp/crimson_gsd.lock
Timeout: 10 minutes
