# 🛠️ Development Setup Guide

Complete guide for setting up the ParagonOCR Web Edition development environment.

## Prerequisites

### Required Software

- **Python 3.10+** (tested on 3.11, 3.12, 3.13)
- **Node.js 18+** (tested on 18.x, 20.x)
- **npm** or **yarn** package manager
- **Git** for version control

### System Dependencies

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install python3.10 python3.10-venv tesseract-ocr poppler-utils
```

#### macOS
```bash
brew install python@3.11 tesseract poppler
```

#### Windows
- Download Python from [python.org](https://python.org)
- Download Tesseract from [GitHub Releases](https://github.com/UB-Mannheim/tesseract/wiki)
- Download Poppler from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases)

### Ollama Setup

Ollama is required for LLM functionality (receipt parsing, chat).

**Installation:**
- **Linux/macOS:** `curl https://ollama.ai/install.sh | sh`
- **Windows:** Download from [ollama.ai](https://ollama.ai)

**Download Model:**
```bash
ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
```

**Verify Installation:**
```bash
ollama list
curl http://localhost:11434/api/tags
```

## Quick Start (5 Minutes)

### Option 1: Using Helper Scripts

```bash
# Clone repository
git clone <repo-url>
cd ParagonOCR

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# Start development servers
./scripts/dev.sh
```

### Option 2: Manual Setup

#### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your configuration

# Initialize database
alembic upgrade head

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Frontend Setup

```bash
# Navigate to frontend (new terminal)
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env.local
# Edit .env.local with API URL

# Start development server
npm run dev
```

#### 3. Verify Setup

- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Detailed Setup

### Backend Configuration

**Environment Variables (.env):**

```ini
# Database
DATABASE_URL=sqlite:///./data/receipts.db
DATABASE_ECHO=false

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
OLLAMA_TIMEOUT=300

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# File Upload
MAX_UPLOAD_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=.pdf,.png,.jpg,.jpeg,.tiff

# Logging
LOG_LEVEL=INFO
```

**Database Migrations:**
```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

### Frontend Configuration

**Environment Variables (.env.local):**

```ini
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

**TypeScript Configuration:**
- Type checking: `npm run type-check`
- Build: `npm run build`
- Preview: `npm run preview`

### Development Tools

#### Backend

**Code Formatting:**
```bash
# Install formatters
pip install black isort

# Format code
black app/
isort app/
```

**Linting:**
```bash
# Install linters
pip install flake8 mypy

# Run linters
flake8 app/
mypy app/
```

**Testing:**
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

#### Frontend

**Code Formatting:**
```bash
# Format with Prettier
npm run format

# Lint with ESLint
npm run lint
```

**Testing:**
```bash
# Run tests
npm run test

# With coverage
npm run test:coverage
```

## IDE Setup

### VS Code

**Recommended Extensions:**
- Python
- Pylance
- ESLint
- Prettier
- Tailwind CSS IntelliSense

**Settings (.vscode/settings.json):**
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python",
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm

1. Open project root
2. Configure Python interpreter: `backend/venv/bin/python`
3. Enable ESLint and Prettier for frontend

## Common Issues

### Ollama Connection Error

**Problem:** `Connection refused` when accessing Ollama

**Solution:**
```bash
# Check if Ollama is running
systemctl --user status ollama  # Linux
# or
ps aux | grep ollama

# Start Ollama
ollama serve
# or
systemctl --user start ollama  # Linux
```

### Tesseract Not Found

**Problem:** `TesseractNotFoundError`

**Solution:**
```bash
# Verify installation
tesseract --version

# Add to PATH if needed
export PATH=$PATH:/usr/local/bin  # macOS
```

### Port Already in Use

**Problem:** Port 8000 or 5173 already in use

**Solution:**
```bash
# Find process using port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process or use different port
uvicorn app.main:app --reload --port 8001
```

### Database Locked

**Problem:** `database is locked` error

**Solution:**
- Close other database connections
- Restart backend server
- Check for long-running transactions

### Frontend Build Errors

**Problem:** TypeScript or build errors

**Solution:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check TypeScript errors
npm run type-check
```

## Development Workflow

### 1. Starting Development

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Ollama (if not running as service)
ollama serve
```

### 2. Making Changes

- **Backend:** Changes auto-reload with `--reload` flag
- **Frontend:** Hot Module Replacement (HMR) enabled
- **Database:** Use Alembic for schema changes

### 3. Testing Changes

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm run test

# Integration tests
pytest tests/integration/ -v
```

### 4. Code Review Checklist

- [ ] Code formatted (black/isort for Python, Prettier for TS)
- [ ] Linting passes (flake8/mypy for Python, ESLint for TS)
- [ ] Tests pass
- [ ] Database migrations created (if schema changed)
- [ ] Environment variables documented
- [ ] API changes documented

## Debugging

### Backend Debugging

**Enable Debug Logging:**
```python
# In .env
LOG_LEVEL=DEBUG
```

**Use Debugger:**
```python
import pdb; pdb.set_trace()  # Python debugger
```

**FastAPI Debug Mode:**
```bash
uvicorn app.main:app --reload --log-level debug
```

### Frontend Debugging

**React DevTools:**
- Install browser extension
- Inspect component state and props

**Network Debugging:**
- Open browser DevTools → Network tab
- Check API requests/responses

**Console Logging:**
```typescript
console.log('Debug:', data);
```

## Next Steps

- Read [Architecture Documentation](../architecture/ARCHITECTURE.md)
- Review [API Reference](../api/API_REFERENCE.md)
- Check [Contributing Guide](CONTRIBUTING.md)

---

**Last Updated:** 2025-12-07  
**Version:** 1.0.0-beta

