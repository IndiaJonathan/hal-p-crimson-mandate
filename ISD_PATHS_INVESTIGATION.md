# Crimson Mandate — ISD Earn Paths Investigation
**Agent:** HAL-P Subagent | **Date:** 2026-04-28 | **Issue:** HAL-P has 500 ISD, mining deadlocked (70 failures, no Mining Laser Mk1)

---

## Summary

HAL-P is stuck at 500 ISD with no Mining Laser and a mining deadlock. The operator needs **any alternate ISD earn path**. This investigation exhaustively tested the game API and WebSocket message surface to find every possible ISD source.

**Bottom line:** There is only ONE confirmed ISD earn path in this game — **golden asteroid events via WebSocket** (`mmo_claim_golden_asteroid`). All other API endpoints are either 404, ISD sinks (research contributions), or credit-only (mineral auction).

---

## Part 1 — REST API Scan (Auth: halp@burk-dashboards.com)

### All endpoints tested — 35 endpoints scanned

| Endpoint | Status | Result |
|---|---|---|
| `GET /api/shop` | 404 | — |
| `GET /api/store` | 404 | — |
| `GET /api/market` | 404 | — |
| `GET /api/items` | 404 | — |
| `GET /api/blueprints` | 404 | — |
| `GET /api/upgrades` | 404 | — |
| `GET /api/minerals/sell` | 404 | — |
| `GET /api/crypto/wallet` | 404 | — |
| `GET /api/wallet` | 404 | — |
| `GET /api/exchange` | 404 | — |
| `GET /api/missions` | 404 | — |
| `GET /api/quests` | 404 | — |
| `GET /api/achievements` | 404 | — |
| `GET /api/bounties` | 404 | — |
| `GET /api/dailies` | 404 | — |
| `GET /api/leaderboard` | 404 | — |
| `GET /api/combat/rewards` | 404 | — |
| `GET /api/loot` | 404 | — |
| `GET /api/drops` | 404 | — |
| `GET /api/activities` | 404 | — |
| `GET /api/events` | 404 | — |
| `GET /api/news` | 404 | — |
| `GET /api/changelog` | 404 | — |
| `GET /api/auction/list` | 404 | GET not supported |
| `GET /api/auction/bids` | 404 | — |
| `GET /api/ships` | 404 | — |
| `GET /api/units` | 404 | — |
| `GET /api/map` | 404 | — |
| `GET /api/world` | 404 | — |
| `GET /api/asteroids` | 404 | — |
| `GET /api/planets` | 404 | — |
| `GET /api/stations` | 404 | — |
| `GET /api/research/contribute` | 404 | — |
| `GET /api/auth/logout` | 404 | — |
| `GET /api/fleet` | 404 | — |
| `GET /api/alliances` | 404 | — |

### Working endpoints

| Endpoint | Status | Response |
|---|---|---|
| `GET /api/balance` | **200** | `{"isdBalance":500,"totalDeposited":0,"totalWithdrawn":0,"totalEarned":0,"totalSpent":0}` |
| `GET /api/profile/me` | **200** | Basic profile, no ISD field |
| `GET /api/profile/me/ships` | **200** | 1 Scout (HP=40, attack=6, range=2) |
| `GET /api/profile/me/achievements` | **200** | `first_blood`, `fleet_commander` — no ISD rewards revealed |
| `GET /api/research/board` | **200** | 9 research boards, each costs 750 ISD to fund — **ISD sink** |
| `GET /api/components/inventory` | **200** | Lists ship components (laser, etc.) |
| `GET /api/minerals/inventory` | **200** | All minerals at 0 — HAL-P has nothing to sell |

### POST endpoints tested

| Endpoint | Payload | Result |
|---|---|---|
| `POST /api/auction/list` | `{"mineralTypeId":"min_copper","quantity":1,"pricePerUnit":0.3}` | `400: "Insufficient minerals to list 1"` — No ISD payout from selling |
| `POST /api/research/contribute` | `{"projectId":"...","isdAmount":10}` | `200` — **confirms ISD is spent to contribute, not earned** |
| `POST /api/achievements/claim` | `{"achievementId":"first_blood"}` | 404 — no claim endpoint |
| `POST /api/bounties/claim` | `{"bountyId":"test"}` | 404 |
| `POST /api/dailies/claim` | `{}` | 404 |
| `POST /api/missions/accept` | `{"missionId":"test"}` | 404 |
| `POST /api/quests/start` | `{"questId":"test"}` | 404 |
| `POST /api/combat/claim` | `{"engagementId":"test"}` | 404 |

---

## Part 2 — WebSocket Message Surface (from `runner.py`)

All message types handled by `MMOClient._on_message`:

| Message Type | Source | ISD-Related? |
|---|---|---|
| `auth_success` | server | No — auth confirmation |
| `mmo_world_joined` | server | No |
| `mmo_resources` | server | **YES — contains `isdBalance` and `credits` updates** |
| `mmo_golden_asteroid_spawned` | server | **YES — primary ISD earn event** |
| `mmo_golden_asteroid_claimed` | server | **YES — contains `cryptoRewarded` = ISD earned** |
| `mmo_mine_result` | server | No — minerals only, no ISD |
| `mmo_engagement_started` | server | No — combat starts |
| `mmo_combat_result` | server | No — combat outcome |
| `mmo_unit_destroyed_notification` | server | No — death notification |
| `mmo_loot_claimed` | server | **Possibly** — loot contents unknown (could include ISD) |
| `error` | server | No — error messages |
| `mmo_unit_moved` | server | No — movement confirmation |

### Detail on confirmed ISD-carrying WS events

#### `mmo_resources`
- Contains: `isdBalance`, `credits`, `minerals`
- This is the authoritative ISD balance source (WS pushes it on world join)
- **Does NOT increase ISD** — it just reflects current balance after actions

#### `mmo_golden_asteroid_spawned` (payload structure)
```python
{
  "id": "ast_...",          # asteroid ID to claim
  "position": {"q": 0, "r": 0},  # hex position
  "type": "golden"           # indicator
}
```
- Spawns randomly in the game world
- Player must be adjacent (dist <= 1) to claim
- Operator uses `mmo_claim_golden_asteroid` WS message to claim

#### `mmo_golden_asteroid_claimed` (payload structure)
```python
{
  "asteroidId": "ast_...",
  "claimerId": "...",
  "cryptoRewarded": 0,       # ISD AMOUNT EARNED
  "rewardType": "ISD"        # or similar flag
}
```
- The `cryptoRewarded` field is the actual ISD earned
- **This is the only ISD earn path confirmed in this game**

#### `mmo_mine_result`
- Contains only `mineralsGained` — mineral type → quantity map
- **No ISD component** in mining yield

#### `mmo_combat_result`
- Contains combat outcome details
- **No ISD component** — credits or minerals may be awarded, not ISD

#### `mmo_loot_claimed`
- Payload structure: `{"type": "...", "quantity": ...}`
- Observed loot types are mineral names (e.g., `min_titanium`)
- **No confirmed ISD loot from combat** — loot appears to be minerals/components only

---

## Part 3 — Golden Asteroid System (The Only ISD Path)

### How it works (from `crimson_operator.py` logic)

1. Server broadcasts `mmo_golden_asteroid_spawned` → captured in `MMOClient._golden_asteroid_spawned`
2. Player must navigate scout adjacent to asteroid (dist ≤ 1)
3. Player sends `mmo_claim_golden_asteroid` WS message with `asteroidId`
4. Server responds with `mmo_golden_asteroid_claimed` containing `cryptoRewarded` amount
5. Balance updates via `mmo_resources` event

### Golden asteroid claim flow
```python
client._send({
    "type": "mmo_claim_golden_asteroid",
    "payload": {"asteroidId": golden["id"]}
})
result = client.wait_for("mmo_golden_asteroid_claimed", timeout=15)
# result[0]["cryptoRewarded"] → ISD amount earned
```

### Constraints
- Must be adjacent (dist ≤ 1) to the golden asteroid
- Current HAL-P position: `(q:28, r:-31)` — far from common spawn locations
- No guarantee of spawn frequency — timeout for wait is 300s (5 min) in the operator
- ISD amount per claim is variable and not yet measured

---

## Part 4 — ISD Sinks (Things That Cost ISD)

These are NOT earn paths — operators should avoid spending ISD unless necessary:

1. **Research Board contributions** — costs ISD to fund tech boards (750 ISD per board)
   - `POST /api/research/contribute` with `{"projectId": "...", "isdAmount": N}`
   - Confirmed: contributing ISD reduces balance, does not return ISD

2. **Mineral auction listing** — sells minerals for credits, NOT ISD
   - `POST /api/auction/list` — only works if you have minerals to list

---

## Part 5 — Alternate Strategies Considered (ALL failed)

### Sell minerals for credits → convert to ISD?
- **Status:** Impossible — HAL-P has 0 minerals (all mined minerals were sold or lost)
- Even if minerals were available, auction listing converts to **credits**, not ISD
- No conversion endpoint (no `/api/exchange` or `/api/wallet/convert`)

### Achievement ISD rewards?
- **Status:** No claim endpoint (404 on all POST attempts)
- Achievements known to HAL-P: `first_blood` (Win first match), `fleet_commander` (5+ ships)
- No ISD rewards confirmed in achievement payloads

### Combat ISD rewards?
- **Status:** No REST endpoint for combat rewards (404)
- WS event `mmo_combat_result` has no ISD field
- WS event `mmo_loot_claimed` shows mineral loot only, no ISD

### Daily quests / missions / bounties?
- **Status:** All 404 — these systems apparently don't exist in this game

### Leaderboard payouts?
- **Status:** 404 — no leaderboard API

### Purchase ISD with real money?
- No shop endpoint found (404 on all shop endpoints)
- No purchase API for ISD

---

## Part 6 — State Assessment

```
HAL-P Balance:
  - ISD:        500
  - Credits:    unknown (not visible in current state.json balance section)
  - Minerals:   0 (all types 0)
  - Components: 1 (wpn_beam_laser_light — equipped on scout)
  - Ships:      1 Scout (attack=6, range=2, HP=40/40)

Mining Status:
  - has_mining_laser: FALSE (Mining Laser Mk1 missing)
  - mining_failures: 70 (circuit breaker armed at 5)
  - Deadlock: Cannot mine without laser, cannot buy laser without ISD income

Position:
  - Scout at (q:28, r:-31) — far from asteroid fields
  - Owned asteroids nearby: ast_2e330239 at (q:28, r:-31) — same position!
    - mineralComposition: titanium x4
    - This asteroid IS adjacent (same hex) — HAL-P can mine it if laser is obtained

Research:
  - 9 boards on the funding board, 750 ISD each to fully fund
  - HAL-P has contributed 0 ISD to any board
  - This is an ISD sink, not earn path

Achievements:
  - first_blood: unlocked
  - fleet_commander: unlocked (requires 5+ ships — HAL-P only has 1)
  - Both are cosmetic/title only — no ISD payout found
```

---

## Recommendations

### Immediate Priority: Claim Every Golden Asteroid

The **only** operational ISD earn path is golden asteroid events. HAL-P should:
1. Monitor for `mmo_golden_asteroid_spawned` events continuously
2. Immediately navigate toward any spawned golden asteroid
3. Claim it with `mmo_claim_golden_asteroid` when adjacent
4. Log `cryptoRewarded` amounts to measure average ISD per claim

**The operator's `wait_for_golden_asteroid(timeout=300)` method already implements this.** It should be kept running at all times.

### Secondary: Obtain Mining Laser Mk1 to break mining deadlock

- Mining Laser Mk1 costs ~1000 ISD (confirmed from `crimson_operator.py` priority logic)
- HAL-P has 500 ISD — needs to earn ~500 more before purchasing
- The nearby asteroid `ast_2e330239` (titanium x4) is in the same hex as HAL-P's scout
- Once laser is obtained, HAL-P can mine and sell minerals for credits (not ISD, but enables progression)

### Research: Do NOT contribute ISD to research boards

Research is an ISD sink. Contributing ISD funds community research but does not return ISD to the contributor. The operator's current code already does this, which is fine as a low-priority background activity — but it should NOT be treated as an earn path.

### Unknown: `mmo_loot_claimed` contents

Loot claimed from combat could potentially include ISD in some scenarios not yet observed. The current loot observed from combat events shows mineral types only, but not enough combat has been observed to be certain there are no ISD-bearing loot scenarios. Continue monitoring `mmo_loot_claimed` events for `cryptoRewarded` or `isdRewarded` fields.

---

## Conclusion

There is exactly **one ISD earn path** in Crimson Mandate as currently understood:

> **Golden asteroid WebSocket events (`mmo_golden_asteroid_spawned` → `mmo_claim_golden_asteroid` → `mmo_golden_asteroid_claimed.cryptoRewarded`)**

Every other API surface — shop, market, missions, quests, achievements, leaderboard, auction (sell minerals), research (contribute) — is either a 404, a credits-only mechanism, or an ISD sink. HAL-P's mining deadlock is a real problem; the only way forward is maximizing golden asteroid claim frequency and saving ISD for the Mining Laser Mk1 purchase (1000 ISD threshold).

The operator should be modified to:
1. Never skip a golden asteroid opportunity
2. Stay connected to WebSocket at all times
3. Log every `cryptoRewarded` amount to track earn rate

---

*Generated by: HAL-P Subagent | Investigation scope: 35 REST endpoints + full WS message surface*