#!/bin/bash
# Crimson Mandate Agent — Entry point
# Usage: ./run.sh

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$AGENT_DIR"

# Activate virtualenv if present
if [ -f "$AGENT_DIR/venv/bin/activate" ]; then
    source "$AGENT_DIR/venv/bin/activate"
fi

# Ensure dependencies
pip install websocket-client requests --quiet 2>/dev/null

# Run the cycle
python3 runner.py
