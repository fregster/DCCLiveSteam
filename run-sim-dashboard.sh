#!/bin/bash
# run-sim-dashboard.sh
# Launch the simulation dashboard using the project virtual environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -x .venv/bin/python ]; then
  echo "[ERROR] Python virtual environment not found. Please set up .venv first."
  exit 1
fi

exec .venv/bin/python -m sim.dashboard
