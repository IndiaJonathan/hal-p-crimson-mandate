#!/usr/bin/env python3
"""Move HALP scout toward Mars and check world state for asteroids"""
import json, subprocess, time

def cmd(script):
    result = subprocess.run(
        ['/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/venv/bin/python', 
         '/Users/jonathan/.openclaw/workspace/crimson-mandate-agent/game.py'] + script.split(),
        capture_output=True, text=True,
        cwd='/Users/jonathan/.openclaw/workspace/crimson-mandate-agent'
    )
    return result.stdout.strip(), result.stderr.strip()

# Current scout position from state: (2,0)
# Mars target: (12,-5)
current_x, current_y = 2, 0
target_x, target_y = 12, -5

# Determine direction to move
dx = target_x - current_x
dy = target_y - current_y

# Move one step in the direction of target
move_x = (1 if dx > 0 else -1) if dx != 0 else 0
move_y = (1 if dy > 0 else -1) if dy != 0 else 0

print(f"Moving from ({current_x},{current_y}) toward ({target_x},{target_y})")
print(f"Direction: dx={move_x}, dy={move_y}")

# Execute move
out, err = cmd(f'move unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_respawn_f696459e {move_x} {move_y}')
print(f"Move result: {out[:500]}")
if err: print(f"Move err: {err[:300]}")

time.sleep(2)

# Check world state for asteroids
out, _ = cmd('ws --json')
try:
    world = json.loads(out)
except:
    print(f"WS parse failed. Output: {out[:200]}")
    world = {}

asteroid_count = 0
for chunk_key in ['chunk_0_0', 'chunk_1_0', 'chunk_0_1', 'chunk_1_1']:
    chunk = world.get(chunk_key, {})
    asteroids = chunk.get('asteroids', [])
    count = len(asteroids)
    if count > 0:
        print(f"*** ASTEROIDS FOUND in {chunk_key}: {asteroids}")
        asteroid_count += count

print(f"\nTotal asteroids visible: {asteroid_count}")

# Find our unit's new position
units = world.get('units', {})
halp = units.get('unit_scout_0a8a2ff5-1b93-44c3-994c-6891e0076d72_respawn_f696459e', {})
pos = halp.get('position', {})
new_x = pos.get('x', '?')
new_y = pos.get('y', '?')
print(f"HALP scout new position: ({new_x},{new_y})")
if new_x != '?':
    print(f"Distance to Mars (12,-5): dx={12-new_x}, dy={-5-new_y}")

# Check fog of war and currentVision
fog = world.get('fogOfWar', {})
cv = world.get('currentVision', {})
print(f"Fog of war entries: {len(fog)}")
print(f"Current vision entries: {len(cv)}")

# Log output for state
with open('/tmp/crimson_move_log.txt', 'w') as f:
    f.write(f"Moved to ({new_x},{new_y}), asteroids={asteroid_count}\n")
    f.write(f"Full output: {out[:1000]}\n")