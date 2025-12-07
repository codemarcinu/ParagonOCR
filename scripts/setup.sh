#!/bin/bash
# ParagonOCR Web Edition - One-command setup script
# Sets up both backend and frontend development environments

set -e  # Exit on error

echo "🧾 ParagonOCR Web Edition - Setup Script"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python $PYTHON_VERSION found"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 18+"
    exit 1
fi
NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
echo "✅ Node.js $(node --version) found"

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama not found. Install from https://ollama.ai"
    echo "   Ollama is required for LLM functionality"
else
    echo "✅ Ollama found"
fi

# Check Tesseract
if ! command -v tesseract &> /dev/null; then
    echo "⚠️  Tesseract OCR not found. Install with:"
    echo "   Linux: sudo apt-get install tesseract-ocr"
    echo "   macOS: brew install tesseract"
    echo "   Tesseract is required for OCR functionality"
else
    echo "✅ Tesseract found"
fi

echo ""
echo "🔧 Setting up backend..."
echo "========================"

# Backend setup
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️  Please edit backend/.env with your configuration"
    else
        echo "Creating default .env file..."
        cat > .env << EOF
# Database
DATABASE_URL=sqlite:///./data/receipts.db
DATABASE_ECHO=false

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
OLLAMA_TIMEOUT=300

# Security
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# File Upload
MAX_UPLOAD_SIZE=10485760
ALLOWED_EXTENSIONS=.pdf,.png,.jpg,.jpeg,.tiff

# Logging
LOG_LEVEL=INFO
EOF
    fi
fi

# Create data directory
mkdir -p data

# Run database migrations
echo "Running database migrations..."
if command -v alembic &> /dev/null || [ -f "venv/bin/alembic" ]; then
    alembic upgrade head || echo "⚠️  Alembic migrations skipped (database may not exist yet)"
else
    echo "⚠️  Alembic not found, skipping migrations"
fi

cd ..

echo ""
echo "🎨 Setting up frontend..."
echo "=========================="

# Frontend setup
cd frontend

# Install dependencies
echo "Installing Node.js dependencies..."
npm install

# Create .env.local if it doesn't exist
if [ ! -f ".env.local" ]; then
    echo "Creating .env.local file..."
    cat > .env.local << EOF
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
EOF
fi

cd ..

echo ""
echo "✅ Setup complete!"
echo "=================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start Ollama (if not running as service):"
echo "   ${BLUE}ollama serve${NC}"
echo ""
echo "2. Download Ollama model:"
echo "   ${BLUE}ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M${NC}"
echo ""
echo "3. Start development servers:"
echo "   ${BLUE}./scripts/dev.sh${NC}"
echo ""
echo "   Or manually:"
echo "   ${BLUE}cd backend && source venv/bin/activate && uvicorn app.main:app --reload${NC}"
echo "   ${BLUE}cd frontend && npm run dev${NC}"
echo ""
echo "4. Access the application:"
echo "   Frontend: ${GREEN}http://localhost:5173${NC}"
echo "   Backend API: ${GREEN}http://localhost:8000${NC}"
echo "   API Docs: ${GREEN}http://localhost:8000/docs${NC}"
echo ""

