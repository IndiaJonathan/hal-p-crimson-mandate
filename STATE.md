# Crimson Mandate GSD — STATE.md
# HAL-P self-executes. No token budget. No subagent chains. Direct action.

## Mission
Break the mining deadlock: ISD 490 → 1000 → buy Mk1 Laser → resume mining.

## Current State
- **ISD:** 489
- **Laser:** Mk0 only; no Mk1 mining laser
- **Mining failures:** 70; circuit breaker remains armed
- **Operator:** `crimson_operator.py` is running and cycling every ~5 minutes
- **Golden hunter:** `golden_hunter_multi.py` is running
- **Self-review cron:** OpenClaw self-review is active
- **Direct GSD cron:** disabled after repeated timeouts; operator + self-review are now the canonical path
- **Token validity:** current session token is still valid through 2026-05-02 UTC
- **Position note:** the live operator log reports the scout idling at `(11,-5)`, while the persisted `state.json` unit snapshot is stale; trust `operator.log` for the freshest live location

## What's Been Tried
- Golden asteroid hunting → only path, no spawns yet
- Combat with EDF → scout dies in 1 round, not viable
- Research contributions → was ISD drain, now disabled
- Sensor Sweep ability → server rejects `mmo_use_ability` message (non-functional)
- All REST API endpoints → 404 or credits-only, no ISD path
- Component selling → no sell endpoint confirmed (64x wpn_beam_laser_light in inventory)

## Current Objective
Find ANY path to 1000 ISD without buying laser with real money.

## Latest Test Results (2026-05-01 13:38 CDT)
### Operator Status
- **Latest live operator balance:** `ISD=489`, `Credits=0`, `Laser=False`, `Failures=70`
- **Latest live operator posture:** circuit breaker active; scout staying idle at `(11,-5)`
- **WebSocket status:** still connecting cleanly on every cycle
- **Deadlock status:** unchanged; no verified path to 1000 ISD without either a golden asteroid event or external game/admin intervention

### Persisted State Health
- **`state.json` freshness problem:** `lastRun` is stale (`2026-04-30T12:48:38Z`) and the stored unit snapshot does not match the live operator log
- **Canonical runtime sources:** use `operator.log` for live behavior and `improvement_log.md` for current review conclusions until state persistence is cleaned up further
- **Legacy cron path:** `job_crimson_mandate.py` repaired syntactically, but the launchd wrapper remains unloaded and is not the active execution path

## Next Actions (Priority Order)
1. **Wait for a golden asteroid spawn** — this remains the only known in-game path that does not require a Mk1 purchase
2. **Refresh auth when the token-renewal reminder fires** — current token expires on 2026-05-02 UTC
3. **Investigate stale `state.json` persistence** — live operator cycles are not updating the persisted snapshot consistently
4. **Re-test component selling only if a sell endpoint is discovered** — no confirmed sell API yet
5. **Keep the direct GSD cron disabled unless it is rewritten to avoid timeout-heavy duplicate work**

## Lock
Lock file: /tmp/crimson_gsd.lock
Timeout: 10 minutes
