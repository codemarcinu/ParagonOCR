#!/bin/bash
# ParagonOCR Web Edition - Cleanup script
# Removes build artifacts, cache files, and temporary files

set -e

echo "🧹 Cleaning ParagonOCR Web Edition..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Python cache
echo "Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.pyd" -delete 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true

# Test artifacts
echo "Cleaning test artifacts..."
rm -f .coverage .coverage.* 2>/dev/null || true
rm -rf htmlcov/ .pytest_cache/ .tox/ 2>/dev/null || true
rm -f test_results.txt 2>/dev/null || true

# Frontend build artifacts
echo "Cleaning frontend build artifacts..."
cd frontend
rm -rf node_modules/.vite dist/ .vite/ 2>/dev/null || true
cd ..

# Log files
echo "Cleaning log files..."
rm -f *.log backend.log frontend.log 2>/dev/null || true
rm -rf logs/*.log 2>/dev/null || true

# OS files
echo "Cleaning OS files..."
find . -type f -name ".DS_Store" -delete 2>/dev/null || true
find . -type f -name "Thumbs.db" -delete 2>/dev/null || true

echo ""
echo "${GREEN}✅ Cleanup complete!${NC}"
echo ""
echo "Note: Virtual environments and node_modules are preserved."
echo "To remove them:"
echo "  rm -rf backend/venv frontend/node_modules"
echo ""

