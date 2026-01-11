#!/bin/bash
set -e

# Base directory
BASE_DIR=$(dirname "$(dirname "$(readlink -f "$0")")")
VENV_DIR="$BASE_DIR/venv"

echo "[INFO] Starting ParagonOCR Backend..."
echo "[INFO] Base Directory: $BASE_DIR"

# Activate venv
source "$VENV_DIR/bin/activate"

# Check dependencies
echo "[INFO] Checking dependencies..."
pip install -r "$BASE_DIR/backend/requirements.txt" > /dev/null 2>&1 || true

# Set path
export PYTHONPATH=$PYTHONPATH:$BASE_DIR/backend

# Run uvicorn
# Reload enabled for development
echo "[INFO] Server running at http://0.0.0.0:8000"
echo "[INFO] Docs available at http://0.0.0.0:8000/docs"
cd "$BASE_DIR/backend" && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
