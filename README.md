# 🧾 ParagonOCR Web Edition

**ParagonOCR Web Edition** is a modern full-stack web application for receipt processing, expense tracking, and AI-powered meal planning. Built with FastAPI, React, and local AI services (Ollama + Tesseract).

[![Version](https://img.shields.io/badge/version-1.0.0--beta-blue)](https://github.com/codemarcinu/paragonocr)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![React](https://img.shields.io/badge/react-19.2-blue)](https://react.dev)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 🚀 Quick Start

### 5-Minute Setup

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

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Ollama** ([install](https://ollama.ai))
- **Tesseract OCR** (`apt-get install tesseract-ocr` or `brew install tesseract`)

**Download Ollama Model:**
```bash
ollama pull SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M
```

---

## ✨ Key Features

### 📄 Receipt Processing
- **Upload receipts** (PDF, PNG, JPG, TIFF)
- **Automatic OCR** (Tesseract)
- **AI parsing** (Ollama/Bielik LLM)
- **Product extraction** & normalization
- **Real-time processing** with WebSocket updates

### 📊 Analytics Dashboard
- **Spending overview** (daily, monthly, yearly)
- **Category breakdown** with charts
- **Shop comparison** and trends
- **Budget tracking** and insights

### 🤖 AI Assistant
- **Local RAG-powered chat** (no cloud required)
- **Meal suggestions** based on available products
- **Recipe recommendations** from your pantry
- **Shopping list generation** with optimization
- **Food waste reduction** tips

### 🛒 Smart Shopping
- **Product search** with fuzzy matching
- **Price history** tracking
- **Auto-generated lists** from meal plans
- **Category management**

---

## 🏗️ Architecture

**Tech Stack:**
- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Frontend:** React 19 + TypeScript + Vite + TailwindCSS
- **AI:** Ollama (local LLM) + Tesseract OCR
- **State:** Zustand
- **Charts:** Recharts

**Architecture Diagram:**
```
Frontend (React) → REST API (FastAPI) → Database (SQLite)
                          ↓
                    Ollama (LLM) + Tesseract (OCR)
```

📖 **Full Architecture:** [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)

---

## 📁 Project Structure

```
ParagonOCR/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── main.py      # FastAPI entry point
│   │   ├── routers/     # API endpoints
│   │   ├── services/    # Business logic
│   │   └── models/      # Database models
│   ├── requirements.txt
│   └── README.md
│
├── frontend/            # React frontend
│   ├── src/
│   │   ├── pages/       # Page components
│   │   ├── components/  # Reusable components
│   │   ├── store/       # Zustand stores
│   │   └── lib/         # Utilities
│   ├── package.json
│   └── README.md
│
├── docs/                # Documentation
│   ├── architecture/    # System design
│   ├── api/             # API reference
│   ├── guides/          # Setup guides
│   ├── analysis/        # Analysis reports
│   └── progress/        # Progress tracking
│
├── archive/             # Legacy desktop code
│   └── desktop/         # Old GUI application
│
├── scripts/             # Helper scripts
│   ├── setup.sh         # One-command setup
│   ├── dev.sh           # Start dev servers
│   └── cleanup.sh       # Clean build artifacts
│
└── README.md            # This file
```

---

## 📚 Documentation

### Quick Links
- **[Development Setup](docs/guides/SETUP_DEV.md)** - Get started developing
- **[API Reference](docs/api/API_REFERENCE.md)** - Complete API documentation
- **[Architecture](docs/architecture/ARCHITECTURE.md)** - System design & components
- **[Database Schema](docs/architecture/DATABASE_SCHEMA.md)** - ER diagrams & tables
- **[Deployment Guide](docs/architecture/DEPLOYMENT.md)** - Production deployment
- **[Contributing](docs/guides/CONTRIBUTING.md)** - How to contribute

### Documentation Index
See [docs/README.md](docs/README.md) for complete documentation index.

---

## 🛠️ Development

### Setup Development Environment

See [docs/guides/SETUP_DEV.md](docs/guides/SETUP_DEV.md) for detailed instructions.

**Quick Start:**
```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm run test
```

### Code Quality

```bash
# Backend formatting
black app/
isort app/

# Frontend formatting
npm run format
npm run lint
```

---

## 🚀 Deployment

### Docker Compose (Recommended)

```bash
docker-compose up -d --build
```

### Manual Deployment

See [docs/architecture/DEPLOYMENT.md](docs/architecture/DEPLOYMENT.md) for:
- Production configuration
- Nginx setup
- Systemd services
- Cloud platform guides (Heroku, AWS, DigitalOcean)

---

## 🔧 Configuration

### Backend (.env)

```ini
# Database
DATABASE_URL=sqlite:///./data/receipts.db

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M

# Security
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:5173

# File Upload
MAX_UPLOAD_SIZE=10485760  # 10MB
```

### Frontend (.env.local)

```ini
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## 🐛 Troubleshooting

### Common Issues

**Ollama not found:**
```bash
# Check if running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

**Tesseract not found:**
```bash
# Linux
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract
```

**Port already in use:**
```bash
# Use different ports
uvicorn app.main:app --reload --port 8001
npm run dev -- --port 5174
```

📖 **More troubleshooting:** [docs/guides/SETUP_DEV.md#common-issues](docs/guides/SETUP_DEV.md#common-issues)

---

## 🤝 Contributing

We welcome contributions! See [docs/guides/CONTRIBUTING.md](docs/guides/CONTRIBUTING.md) for:
- Development guidelines
- Code style requirements
- Pull request process
- Testing requirements

---

## 📊 Project Status

**Current Version:** 1.0.0-beta

**Status:** ✅ Active Development

**Completed:**
- ✅ Backend API (FastAPI)
- ✅ Frontend UI (React)
- ✅ OCR integration (Tesseract)
- ✅ LLM integration (Ollama)
- ✅ Receipt processing pipeline
- ✅ Analytics dashboard
- ✅ AI chat with RAG

**In Progress:**
- 🔄 RAG service optimization
- 🔄 WebSocket real-time updates
- 🔄 Comprehensive testing

**Recently Added:**
- ✅ FIDO2 WebAuthn Passkeys authentication

**Planned:**
- 📋 WebSocket support for real-time chat
- 📋 Analytics dashboard enhancements
- 📋 Performance optimizations
- 📋 CI/CD pipeline
- 📋 Mobile app (future)

📖 **Progress Tracking:** [docs/progress/](docs/progress/)

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Ollama** - Local LLM inference
- **Tesseract OCR** - Text extraction
- **FastAPI** - Modern Python web framework
- **React** - UI framework
- **SpeakLeash** - Bielik Polish language model

---

## 📞 Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/codemarcinu/paragonocr/issues)
- **Discussions:** [GitHub Discussions](https://github.com/codemarcinu/paragonocr/discussions)

---

## 🔗 Related Projects

- **Legacy Desktop Version:** See [archive/desktop/](archive/desktop/) for the old GUI application
- **ReceiptParser:** Legacy parsing library (archived)

---

**Last Updated:** 2025-12-07  
**Maintained by:** [CodeMarcinu](https://github.com/codemarcinu)

---

> **Note:** This is the **Web Edition** of ParagonOCR. For the legacy desktop version, see [archive/desktop/](archive/desktop/).
