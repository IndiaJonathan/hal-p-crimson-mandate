# Crimson Mandate Agent

Autonomous agent harness for [Crimson Mandate](https://crimsonmandate.com/) — a free-to-earn blockchain space MMO.

## What It Does

- Authenticates via WebSocket using stored JWT session
- Syncs empire state (minerals, ISD balance, ships, research boards)
- Fetches live world state (units, asteroids, planets, stations)
- Runs a rule-based decision engine to pick the next action
- Executes actions via REST API or WebSocket
- Persists state to `state.json` between cycles

## Architecture

```
crimson-mandate-agent/
├── runner.py         # Main cycle: REST sync → WS world state → decide → act
├── decisions.py      # Rule engine: mining, selling, research contribution
├── memory.py         # State persistence (read/write state.json)
├── auth.py           # Login + token refresh
├── state.json       # Persistent agent memory
├── session_token.txt # Current JWT (auto-managed)
├── venv/            # Python virtualenv (pip install websocket-client requests)
├── run.sh           # Entrypoint
└── state.json       # Persistent state
```

## Quick Start

```bash
cd crimson-mandate-agent
./run.sh
```

## Auth Setup

```bash
./venv/bin/python3 auth.py <email> <password>
```

## Current Status

- **Account:** `halp@burk-dashboards.com` / `Test1234!`
- **Commander:** HALP (userId: `0a8a2ff5-1b93-44c3-994c-6891e0076d72`)
- **ISD Balance:** 0 (needs gameplay to earn)
- **Ships:** Scout (×1)
- **Starter Entities:** Scout at (-12, 10) in Core zone

## Game Loop

| Priority | Action | Notes |
|----------|--------|-------|
| 1 | REST sync | Profile, balance, minerals, ships |
| 2 | WS world state | Units, asteroids, planets |
| 3 | Move toward asteroid | If scout far from target |
| 4 | Mine asteroid | Fails without Mining Laser Mk1 ($1) |
| 5 | Sell minerals | When above threshold |
| 6 | Contribute to research | If ISD ≥ 50 |

## Known Limitations

1. **Mining requires $1 upgrade** — Scout comes with no Mining Laser. Buying Mining Laser Mk1 ($1 USD) via component shop is needed to start mining.
2. **Token refresh** — JWT tokens may expire; re-run `auth.py` to refresh.
3. **Scout is a combat ship** — 2× Beam Lasers, not a miner. Consider buying a Mule Mk1 ($20) or Space Tug for efficient hauling.

## Cron Schedule

LaunchAgent runs every **30 minutes**. Config: `~/Library/LaunchAgents/com.burk.crimson-mandate-agent.plist`

```bash
# View logs
tail -f ~/.openclaw/workspace/reports/crimson-mandate-agent.log

# Run manually
./venv/bin/python3 runner.py

# Stop cron
launchctl unload ~/Library/LaunchAgents/com.burk.crimson-mandate-agent.plist
```

## WebSocket API

- **URL:** `wss://crimsonmandate.com/ws`
- **Auth:** `{"type": "auth", "payload": {"sessionId": "<JWT>"}}`
- **World Join:** `{"type": "mmo_join_world", "payload": {"worldId": 1}}`
- **Move:** `{"type": "mmo_move_unit", "payload": {"unitId": "...", "targetHex": {"q": -12, "r": 10}}}`
- **Mine:** `{"type": "mmo_mine_asteroid", "payload": {"unitId": "...", "asteroidId": "..."}}`
- **Resources:** `{"type": "mmo_get_resources", "payload": {"worldId": 1}}`

## REST API Base

- **Base:** `https://crimsonmandate.com`
- **Auth header:** `Authorization: Bearer <JWT>`
- Key endpoints: `/api/profile/me`, `/api/balance`, `/api/minerals/inventory`, `/api/purchase/ship`, `/api/research/board`, `/api/research/contribute`
