# Crimson Mandate — Agent Strategy & Self-Improvement Guide

## Mission
Build a self-improving autonomous agent that earns ISD and crypto by playing Crimson Mandate without spending real money. Continuously analyze past runs, fix failures, optimize loops, and expand capabilities.

## Core Loop (Every 15 Minutes)
1. Sync REST state (balance, ISD, minerals, ships)
2. Fetch world state via WebSocket
3. Decision engine: prioritize most impactful action
4. Execute action (REST or WS)
5. Log result → analyze → improve → commit changes

## Priority Queue (Resource Gaining)

### P0 — Immediate Revenue
1. **Combat** → defeat EDF NPCs → loot drops → sell for ISD
2. **Mining** (requires Mining Laser Mk1 — $1) → mine → sell minerals on auction
3. **Golden Asteroids** → mine → deliver to Earth → earn ISD/crypto

### P1 — Empire Building
4. **Colonize planets** → own territory → passive ISD
5. **Research contributions** → 50+ ISD → public boards → LP revenue share
6. **Station deployment** → earn from other players' trading

### P2 — Optimization
7. **Fleet expansion** → buy fighters/miners
8. **Component upgrades** → improve ship stats
9. **Alliance formation** → shared vision + LP revenue

## Known Blockers & Solutions

| Blocker | Solution | Status |
|--------|----------|--------|
| No Mining Laser Mk1 ($1) | Combat loot drops | ⏳ In progress |
| WS attack delivery unreliable | Switch to blocking recv() in runner | 🔧 Fixing |
| Scout Mk0 (basic laser) weak | Win combat → buy Mk1 laser | ⏳ Pending |
| EDF Fighter has 100 HP | Multiple attacks over cycles | ✅ Working |

## Self-Improvement Protocol

### Per-Cycle Analysis
After each run, check `runner.log` for:
- Any `error` or `FAILED` — fix immediately
- Actions taken vs resources gained — if no resources in 3 cycles, escalate
- Missing API responses — check server health
- Combat outcomes — adjust attack strategy if losing

### Per-Day Analysis
1. Review action log for patterns
2. Check if ISD/balance growing
3. Identify stuck states (same action repeated)
4. Push improvements to GitHub

### Improvement Ideas (Backlog)
- [ ] Intercept loot drops from combat (auto-claim)
- [ ] Find golden asteroid spawn locations
- [ ] Implement optimal pathfinding (A* hex movement)
- [ ] Auto-buy Mining Laser when ISD > $1
- [ ] Predict component drop rates from EDF
- [ ] Monitor auction house for flip opportunities
- [ ] Multi-ship coordination (squad tactics)
- [ ] Research board optimal contribution strategy
- [ ] WebSocket reconnects with exponential backoff
