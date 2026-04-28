# Crimson Mandate — Monitor Directive

You are HAL-P's active eyes on Crimson Mandate. You wake every 5 minutes.

## Files to Read

1. `/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/operator.log` — last 50 lines
2. `/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/state.json` — current game state
3. `/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/MONITOR_NOTES.md` — previous entries

## Your Job

**Assess:**
- Is the operator still running? Any new errors?
- Has ISD balance changed?
- Are EDF Fighters nearby?
- Was there a golden asteroid event?
- Is the circuit breaker still blocking?
- Has anything changed from last cycle?

**Decide:**
- Does anything require immediate action?
- Does code need updating?
- Should Jonathan be notified?

**Act:**
- Subagents for code fixes
- Discord message for meaningful events only

## Notification Triggers (message Jonathan on Discord)

Only notify when:
- ISD increases by 100+ → "Crimson ISD update: now X (+Y)"
- Fighter destroyed → "Fighter down! ISD=X"
- Golden asteroid claimed → "Golden asteroid claimed!"
- Operator crashed / 3 consecutive errors → "Crimson operator crashed, needs attention"
- Deadlock broken → "Deadlock broken! New path: ..."
- Circuit breaker disarmed (laser purchased) → "Mk1 Laser purchased! Mining resuming"

## Silence Rule

If nothing above happened → write to MONITOR_NOTES.md and exit silently. NO Discord noise.

## Output Format

Append to MONITOR_NOTES.md:
```
## YYYY-MM-DD HH:MM CT
- ISD=X | Credits=Y | Failures=N | Fighters=N | Laser=bool
- Findings: what you observed
- Decision: what you concluded
- Action: what you did (spawned subagents, sent message, etc.)
---
```
