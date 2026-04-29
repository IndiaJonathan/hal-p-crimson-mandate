# COMBAT_STRATEGY.md — Crimson Mandate Combat ISD Viability

**Agent:** Crimson Mandate Combat Strategist | **Date:** 2026-04-28
**Operator Position:** Scout at (q:28, r:-31) | **Balance:** 490 ISD | **Goal:** 1000 ISD for Mk1 Laser

---

## EDF Unit Map

**Status:** WebSocket session invalidated — current stored token is expired (HTTP 200 HTML response instead of JSON). Fresh auth via `auth.py` (re-login) was successful but WS session expired before full world-state snapshot could complete. EDF unit map is based on **historical combat logs** (operator.log lines ~335-338, 742-745) and the prior full world-state capture from the ISD_PATHS investigation.

### Known EDF Presence (from combat log snapshot near Earth area)

| Hex Location | Unit Type(s) | Notes |
|---|---|---|
| (q:100, r:99) | Cruiser x2, Battleship x1 | Combat occurred here — AI_BOUNTY vs HAL-P's Cruiser |
| (q:99, r:99) | Cruiser x1 | Engaged HAL-P's Cruiser at (q:100, r:99) |
| (q:96-98, r:90-93) | Battleship x2, Cruiser x2 | AI_BOUNTY vs doover's Battleship |
| ~Earth area (inferred) | Multiple EDF fighters | Operator has been "seeking EDF" toward Earth since day 1 |
| (q:27, r:4) | Cruiser x1 | Confirmed in later combat log — different location |

**Key observations from combat logs:**
- EDF uses: Gauss Rifle (25 dmg), Flak Array (21 dmg), Missile Launcher (27 dmg), Laser PD (22 dmg), Plasma Cannon
- HP values seen: Cruiser ~240, Battleship ~337-2000
- All combat observed was between AI ships (AI_BOUNTY faction), NOT EDF vs player
- The operator has **never actually engaged EDF** — it has been seeking toward Earth for ~165 cycles with no confirmed EDF kill logged

**EDF cluster assessment:** Based on operator.log history (all cycles ending in "Seeking EDF — moved toward Earth"), EDF presence appears concentrated near Earth at (q:0, r:0). Scout currently at (28,-31) — ~39 hexes from Earth.

---

## Combat Loot Analysis

### What the code says

From `runner.py` line 161 handler:
```python
elif msg_type == "mmo_unit_destroyed_notification":
    logger.info(f"💀 Unit destroyed: {payload.get('unitId')} by {payload.get('killedBy')}")
elif msg_type == "mmo_loot_claimed":
    logger.info(f"🎁 Loot: {payload}")
```

The loot handler logs the raw payload but **no ISD field has ever been observed** in loot. All `mmo_loot_claimed` events observed in operator.log contain only mineral types.

### The verdict from exhaustive investigation (ISD_PATHS_INVESTIGATION.md)

- **`mmo_golden_asteroid_claimed` → `cryptoRewarded` = ISD earned** — the ONLY ISD earn path confirmed
- **`mmo_combat_result` → no ISD field** — combat resolves without any ISD transfer
- **`mmo_loot_claimed` → mineral loot only** — `{"type": "min_titanium", "quantity": N}` format
- **`mmo_unit_destroyed_notification` → death notification only** — no rewards
- REST API `/api/combat/rewards` → 404 (does not exist)
- REST API `/api/loot`, `/api/drops`, `/api/bounties` → all 404

**Conclusion: Combat does NOT pay ISD. There is no combat-based ISD reward path.**

---

## Scout vs Fighter Matchup

### Scout stats
- HP: 40
- Attack: 6 (Beam Laser Mk1, range=2)
- Speed: 1 hex per move action
- No shield (from observed combat logs — no shieldDamage on player units in combat)

### EDF Fighter stats (from combat logs)
EDF Cruiser:
- HP: ~240 (from combat log attackerHp=240, defenderHp=240)
- Weapons: Gauss Rifle (25 dmg), Flak Array (21 dmg)
- Accuracy thresholds: ~90.3 for Gauss, 95 for Flak

EDF Battleship:
- HP: 337–2000 (range wide — multiple ship tiers)
- Weapons: Missile Launcher (27 dmg), Laser PD (22 dmg), Gauss Rifle (25 dmg)

### Can the scout survive?

**Against a Cruiser (HP ~240):**
- Scout deals 6 damage per attack (Beam Laser)
- Attacks needed: ceil(240/6) = **40 attacks** to kill one EDF Cruiser
- Scout HP: 40 (no shields)
- Enemy retaliation per round (Gauss + Flak): ~25 + 21 = **46 damage** if both hit
- Scout dies in **1 round of combat** if attacked by EDF

**Against a Battleship (HP 337+):**
- Even more attacks needed: ceil(337/6) = **57 attacks**
- Higher damage output: Missile Launcher (27) + Laser PD (22) = ~49 per round
- Scout dies in **1 round**

**The scout CANNOT survive direct combat with any EDF unit.** Even if the scout attacks first, EDF retaliates in the same engagement round with lethal damage. The scout's HP of 40 is insufficient to absorb even one full enemy attack round.

Even if we assume the scout could kite (range=2 vs enemy range=1), the moment the scout enters combat it takes lethal return fire.

### Movement to reach EDF

- Scout current position: (q:28, r:-31)
- EDF near Earth: (q:0, r:0) — minimum ~39 hexes away (cube distance)
- Each cycle: 1 hex movement → **minimum ~39 cycles = ~195 minutes** to reach EDF zone

---

## EDF Respawn

**Status: Unknown.** No evidence of EDF respawn observed in operator.log. The operator has never killed an EDF unit so there is no respawn data. The game uses engagement_started/engagement_ended patterns for AI-vs-AI combat, suggesting EDF units may be persistent NPC guards rather than dynamic spawns.

No respawn timer data available.

---

## Credits Conversion

**No conversion path exists.** From the exhaustive API scan:

| Endpoint | Result |
|---|---|
| `POST /api/exchange` | 404 |
| `POST /api/wallet/convert` | 404 |
| `POST /api/credits/purchase` | 404 |
| `POST /api/credits/buy` | 404 |
| `POST /api/auction/list` | Works, but sells minerals for **credits** — no ISD conversion |

- Credits earned from selling minerals **cannot be converted to ISD**
- There is no ISD purchase mechanism (no shop found)
- No real-money purchase path found

---

## Recommended Action Plan

### Immediate Assessment: Combat is NOT a viable ISD earn path

**The fundamental problem:** Even if the operator reaches EDF, the scout is destroyed in a single combat round. The scout has HP=40 vs enemy damage output of 46+ per round. There is no scenario where the scout can kill EDF and survive.

Therefore **combat cannot replace golden asteroids as the primary ISD earn path.**

### What the operator should do instead

1. **Continue golden asteroid hunting** — this is the only ISD earn path
2. **Do not move scout away from viable golden asteroid zones** — the scout at (28,-31) is in a known titanium asteroid position. If golden asteroids spawn near current position, it can respond faster than from Earth orbit.
3. **The 490→1000 ISD gap is ~510 ISD** — this is achievable through persistent golden asteroid claim patience

### If operator insists on combat approach

The only viable combat progression would require:
1. Acquire additional ships (5 ships for `fleet_commander` achievement — potential future ISD reward?)
2. Each ship would need HP > 50 to survive EDF retaliation
3. No confirmed ISD reward from achievement system exists — this is speculative

### What is NOT recommended
- Moving toward Earth to "seek EDF combat" — wastes cycles, scout dies on arrival
- Expecting combat loot to contain ISD — never observed
- Expecting credits→ISD conversion — does not exist

---

## Summary Table

| Question | Answer |
|---|---|
| Does combat pay ISD? | **NO** — only golden asteroid claims pay ISD |
| Can scout survive EDF? | **NO** — 40 HP vs 46+ damage per round |
| Movement time to Earth/EDF? | ~39 cycles (~195 min) minimum |
| EDF respawn rate? | **Unknown** — no kills ever recorded |
| Credits→ISD conversion? | **Impossible** — no conversion endpoint |
| Combat viable for ISD? | **NO** — must rely on golden asteroid path only |

---

*Generated by: Crimson Mandate Combat Strategist subagent*
*Data sources: runner.py code analysis, operator.log combat events, ISD_PATHS_INVESTIGATION.md*