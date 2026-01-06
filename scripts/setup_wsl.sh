#!/bin/bash
set -e

echo "Starting WSL Setup for ParagonOCR..."

# 1. Install System Dependencies
echo "Installing system dependencies..."
sudo apt update
sudo apt install -y python3-venv python3-pip \
    tesseract-ocr tesseract-ocr-pol \
    poppler-utils \
    libgl1

# 2. Setup Python Environment
echo "Setting up Python environment..."
PROJECT_ROOT="/mnt/d/projekty/ParagonOCR"
if [ -d "$PWD/backend" ]; then
    PROJECT_ROOT="$PWD"
fi

echo "Project root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Clean old venv if it exists
if [ -d "backend/venv" ]; then
    echo "Removing old venv..."
    rm -rf backend/venv
fi

# Create new venv
echo "Creating new venv..."
python3 -m venv backend/venv
source backend/venv/bin/activate

# 3. Install Python Dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
if [ -f "backend/requirements.txt" ]; then
    pip install -r backend/requirements.txt
else
    echo "Warning: backend/requirements.txt not found!"
fi

# Install critical fixes
pip install pypdf opencv-python-headless pdf2image

echo "Setup Complete!"
echo "To activate the environment run: source backend/venv/bin/activate"
