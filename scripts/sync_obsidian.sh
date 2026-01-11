#!/bin/bash
# Wrapper script to run the Obsidian import tool from the project root in WSL

# Ensure we are in the project root
cd "$(dirname "$0")/.."

# Go to backend to load .env correctly
cd backend

# Run the python script using the backend virtual environment
# Default path is ~/obsidian, can be overridden by arguments
./venv/bin/python ../scripts/import_obsidian.py --path "${1:-~/obsidian}"
