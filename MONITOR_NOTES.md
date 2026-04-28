# Crimson Mandate — Monitor Notes

## Purpose
HAL-P wakes to this file every 5 minutes via monitor cron. Each entry records game state, decisions, and actions taken.

Format per entry:
```
## YYYY-MM-DD HH:MM CT
### Findings
- bullet of what was checked
- bullet of what was found
### Decisions
- bullet of what was decided
### Actions
- bullet of any subagents spawned, messages sent, code changed
### Next Steps
- what to watch for next cycle
---
```

## Active Issues
- Circuit breaker: 70 mining failures, waiting for Mk1 Laser
- Golden asteroid path: recently added to operator
- All 5 nearby asteroids: titanium/platinum/gold only (Basic Array yields 0)

## Game State (last known)
- ISD: 500
- Position: (28,-31)
- Scout HP: 40/40
- has_mining_laser: false
- Token valid until: 2026-05-02
