#!/bin/bash

# Standalone Slack Bot Runner for PANDA SDL
# This script runs the PANDA Slack bot as a standalone process

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Activate virtual environment if it exists
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
elif [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
elif command -v conda &> /dev/null; then
    # Fallback to conda if available
    source ~/anaconda3/etc/profile.d/conda.sh 2>/dev/null || true
    conda activate python310 2>/dev/null || conda activate python311 2>/dev/null || true
fi

# Run the standalone Slack bot script
cd "$PROJECT_ROOT"
python scripts/panda-slack-bot.py "$@"

