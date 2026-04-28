# Crimson Mandate — Code Fix Directive

Use this when the MONITOR agent detects a code issue that needs a subagent.

## Before Starting
Read: `/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/crimson_operator.py` and relevant runner files.

## Issue Types

**1. Operator logic gap**
- Identify the missing behavior
- Edit crimson_operator.py to add the behavior
- Test the change conceptually
- Commit to git

**2. New game feature discovered**
- Investigate the feature by checking API endpoints
- Add the feature handler to the operator
- Commit to git

**3. Crash/error in operator log**
- Identify root cause from traceback
- Fix the bug
- Commit to git

## Rules
- Keep changes minimal and surgical
- Do not rewrite entire files unless necessary
- Always commit after fixing
- Write a brief summary of the fix to MONITOR_NOTES.md

## Discord Message to Jonathan
If you fix something meaningful, message him:
"Fixed: [brief description of what was broken and what you changed]"
