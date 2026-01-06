# ParagonOCR Web Edition - Setup Script (Windows PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "🧾 ParagonOCR Web Edition - Setup Script" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""

# Check prerequisites
Write-Host "📋 Checking prerequisites..."

# Check Python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}
$pythonVersion = python --version
Write-Host "✅ $pythonVersion found"

# Check Node.js
if (-not (Get-Command "node" -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}
$nodeVersion = node --version
Write-Host "✅ Node.js $nodeVersion found"

# Check Ollama
if (-not (Get-Command "ollama" -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️  Ollama not found. Install from https://ollama.ai" -ForegroundColor Yellow
    Write-Host "   Ollama is required for LLM functionality"
} else {
    Write-Host "✅ Ollama found"
}

# Check Tesseract
if (-not (Get-Command "tesseract" -ErrorAction SilentlyContinue)) {
    # Check common locations
    if (Test-Path "C:\Program Files\Tesseract-OCR\tesseract.exe") {
        Write-Host "✅ Tesseract found at C:\Program Files\Tesseract-OCR\tesseract.exe"
    } else {
        Write-Host "⚠️  Tesseract OCR not found in PATH or standard location." -ForegroundColor Yellow
        Write-Host "   Please install Tesseract and ensure it's in your PATH or update backend/.env"
    }
} else {
    Write-Host "✅ Tesseract found in PATH"
}

Write-Host ""
Write-Host "🔧 Setting up backend..."
Write-Host "========================"

# Backend setup
Set-Location "backend"

# Create virtual environment if it doesn't exist
# Check if venv exists
if (Test-Path "venv") {
    # Check if it's a valid Windows venv (has Scripts folder)
    if (-not (Test-Path "venv\Scripts")) {
        Write-Host "⚠️  Detected invalid or non-Windows virtual environment (likely from WSL/Linux)." -ForegroundColor Yellow
        Write-Host "   Removing old environment and recreating..."
        Remove-Item -Recurse -Force "venv"
        Write-Host "Creating Python virtual environment..."
        python -m venv venv
    } else {
        Write-Host "✅ Virtual environment found"
    }
} else {
    Write-Host "Creating Python virtual environment..."
    python -m venv venv
}

# Activate virtual environment and install dependencies
# Note: We can't easily activate venv in the current script context for subsequent commands in a lasting way 
# without dot sourcing, but for installation it's better to use the direct path to pip.
Write-Host "Installing Python dependencies..."
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\pip.exe install -r requirements.txt

# Create .env if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file from .env.example..."
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "⚠️  Please edit backend/.env with your configuration" -ForegroundColor Yellow
    } else {
        Write-Host "Creating default .env file..."
        $secretKey = -join ((0..32) | ForEach-Object { "{0:x}" -f (Get-Random -Max 16) })
        $content = @"
# Database
DATABASE_URL=sqlite:///./data/receipts.db
DATABASE_ECHO=false

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
OLLAMA_TIMEOUT=300

# Security
SECRET_KEY=$secretKey
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# File Upload
MAX_UPLOAD_SIZE=10485760
ALLOWED_EXTENSIONS=.pdf,.png,.jpg,.jpeg,.tiff

# Logging
LOG_LEVEL=INFO

# OCR
OCR_ENGINE=tesseract
# Set this if Tesseract is not in PATH
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
# Set this for PDF conversion
# POPPLER_PATH=C:\Program Files\poppler-xx.xx.xx\Library\bin
"@
        Set-Content -Path ".env" -Value $content -Encoding utf8
    }
}

# Create data directory
if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

# Run database migrations
Write-Host "Running database migrations..."
if (Test-Path "venv\Scripts\alembic.exe") {
    & .\venv\Scripts\alembic.exe upgrade head
} else {
    Write-Host "⚠️  Alembic not found, skipping migrations" -ForegroundColor Yellow
}

Set-Location ".."

Write-Host ""
Write-Host "🎨 Setting up frontend..."
Write-Host "=========================="

# Frontend setup
Set-Location "frontend"

# Install dependencies
Write-Host "Installing Node.js dependencies..."
npm install

# Create .env.local if it doesn't exist
if (-not (Test-Path ".env.local")) {
    Write-Host "Creating .env.local file..."
    $content = @"
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
"@
    Set-Content -Path ".env.local" -Value $content -Encoding utf8
}

Set-Location ".."

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host "=================="
Write-Host ""
Write-Host "Next steps:"
Write-Host ""
Write-Host "1. Start Ollama (if not running):"
Write-Host "   ollama serve" -ForegroundColor Blue
Write-Host ""
Write-Host "2. Download Ollama model:"
Write-Host "   ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M" -ForegroundColor Blue
Write-Host ""
Write-Host "3. Start development servers:"
Write-Host "   .\scripts\dev.ps1" -ForegroundColor Blue
Write-Host ""
