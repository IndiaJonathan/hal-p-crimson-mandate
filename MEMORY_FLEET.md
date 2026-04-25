# Fleet Coordinator — Design

## Concept
Multiple account Scouts form a "patrol fleet" — move together, attack together, share target discovery.

## Accounts (4 registered)
- HALP-1: halp@burk-dashboards.com (Scout at ~(-19, 22))
- HALP-2: halp2@burk-dashboards.com (Scout at (0,0))
- HALP-3: halp3@burk-dashboards.com (Scout at (0,0))
- HALP-4: halp4@burk-dashboards.com (Scout at (0,0))

## Key Questions
1. Do multiple Scouts attacking same EDF deal cumulative damage? → LIKELY YES (shared-world MMO)
2. What loot does EDF drop? → UNKNOWN (need to kill one and check)
3. Do EDF units respawn? How fast? → UNKNOWN

## Fleet Patrol Strategy
1. All Scouts converge on Core zone center (0,0)
2. Move in formation (spread ~3 hexes apart for vision coverage)
3. When EDF found: ALL Scouts attack same target
4. If EDF HP shared: 4×3=12 dmg/round → 9 rounds to kill EDF Scout (vs 34 solo)
5. Scout HP: 40 — EDF deals 3/round → can survive ~13 rounds

## Next Test
1. Move HALP-1 Scout to (0,0) — DONE
2. All Scouts converge on Core patrol zone
3. Find EDF → test coordinated 4-account attack
4. Check loot drops

## Multi-Account Scaling
- Each account is free to register
- Optimal fleet: 5-10 accounts
- Each account = 1 Scout (combat unit)
- Coordinator script manages all simultaneously
