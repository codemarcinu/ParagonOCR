# ParagonOCR Web Edition - Kompleksowy Przewodnik

## 📋 Spis Treści
1. [Architektura](#architektura)
2. [Szybki Start](#szybki-start)
3. [Instrukcje Instalacji](#instrukcje-instalacji)
4. [Struktura Projektu](#struktura-projektu)
5. [JSON Prompt dla Cursora](#json-prompt-dla-cursora)
6. [Roadmap Implementacji](#roadmap-implementacji)

---

## Architektura

### High-Level Overview
```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React 18+)                     │
│  ┌──────────────┬──────────────┬──────────────┐             │
│  │  Dashboard   │   Receipts   │     Chat AI  │             │
│  │   Upload     │    Viewer    │   Assistant  │             │
│  │  Analytics   │   Products   │  Analytics   │             │
│  └──────────────┴──────────────┴──────────────┘             │
│                          ▼                                    │
│                   REST API + WebSocket                       │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐  ┌──────────────┐
│   FastAPI    │   │   Ollama     │  │  Tesseract   │
│   Backend    │   │   (LLM)      │  │    (OCR)     │
│              │   │   bielik     │  │              │
│  - Database  │   └──────────────┘  └──────────────┘
│  - RAG       │
│  - Analytics │
│  - Auth      │
└──────────────┘
        ▼
┌──────────────┐
│   SQLite     │
│  Database    │
└──────────────┘
```

### Komponenty Systemu

#### 1. **Frontend (React + TypeScript + Vite)**
- **Strony:** Dashboard, Receipts, Products, Analytics, Shopping List, Chat
- **Komponenty:** Upload, Viewer, Search, Charts, Chat UI
- **State Management:** Zustand (lean & performant)
- **Styling:** TailwindCSS + custom design system

#### 2. **Backend (FastAPI + SQLAlchemy)**
- **OCR Service:** Tesseract wrapper (PDF + images)
- **LLM Service:** Ollama client (receipt parsing, chat, RAG)
- **Database:** SQLAlchemy ORM + SQLite
- **Analytics:** Spending patterns, trends, recommendations
- **RAG Engine:** Semantic search over receipts + knowledge base

#### 3. **Local Services**
- **Ollama:** LLM inference (bielik - Polish model)
- **Tesseract:** OCR text extraction
- **Sentence Transformers:** Embeddings for RAG

#### 4. **Database Schema**
```sql
Receipt (id, date, shop, total, image_path, status)
ReceiptItem (id, receipt_id, product_id, quantity, unit_price, total)
Product (id, name, normalized_name, category_id, unit)
Category (id, name, color, icon)
ShoppingList (id, items_json, created_at, completed_at)
ChatHistory (id, query, response, timestamp, context)
```

---

## Szybki Start

### Wymagania Systemowe
- **Python:** 3.10+
- **Node.js:** 18+
- **Ollama:** pobrać z [ollama.ai](https://ollama.ai)
- **Tesseract:** `apt-get install tesseract-ocr` (Linux) lub `brew install tesseract` (Mac)

### Instalacja (5 minut)

```bash
# 1. Klonuj projekt
git clone <repo>
cd ParagonOCR-Web

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Przygotuj Ollama
ollama pull bielik  # Pobierz model
# Ollama będzie dostępne na localhost:11434

# 4. Database migrations
alembic upgrade head

# 5. Start backend
uvicorn app.main:app --reload

# 6. Frontend setup (nowy terminal)
cd ../frontend
npm install
npm run dev

# 7. Otwórz http://localhost:5173
```

---

## Instrukcje Instalacji

### Windows 10/11

```powershell
# 1. Python 3.10+ (z https://python.org)
# 2. Tesseract (z https://github.com/UB-Mannheim/tesseract/wiki)
# 3. Ollama (z https://ollama.ai)

# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ..\frontend
npm install
npm run dev
```

### macOS

```bash
# Homebrew
brew install python@3.11 tesseract

# Download Ollama from https://ollama.ai
# Or: brew install ollama

# Setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
npm run dev
```

### Linux (Ubuntu/Debian)

```bash
# Dependencies
sudo apt-get update
sudo apt-get install python3.10 python3.10-venv tesseract-ocr

# Node.js (if not installed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install nodejs

# Ollama
curl https://ollama.ai/install.sh | sh

# Setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
npm run dev
```

### Docker (Optional)

```bash
# Backend container
docker build -f backend/Dockerfile -t paragonocr-backend .
docker run -p 8000:8000 -v $(pwd)/data:/app/data paragonocr-backend

# With Ollama
docker-compose up
```

---

## Struktura Projektu

```
ParagonOCR-Web/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Configuration (env vars)
│   │   ├── database.py             # SQLAlchemy models
│   │   ├── models/                 # Data models (Pydantic)
│   │   ├── services/               # Business logic
│   │   │   ├── ocr_service.py     # Tesseract OCR wrapper
│   │   │   ├── llm_service.py     # Ollama client
│   │   │   ├── rag_service.py     # RAG engine
│   │   │   └── analytics_service.py
│   │   └── routers/                # API endpoints
│   │       ├── receipts.py
│   │       ├── products.py
│   │       ├── chat.py
│   │       └── analytics.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Receipts.tsx
│   │   │   ├── Products.tsx
│   │   │   ├── Analytics.tsx
│   │   │   ├── ShoppingList.tsx
│   │   │   └── Chat.tsx
│   │   ├── components/
│   │   │   ├── ReceiptUploader.tsx
│   │   │   ├── ReceiptViewer.tsx
│   │   │   ├── ChatUI.tsx
│   │   │   ├── ProductSearch.tsx
│   │   │   └── SpendingChart.tsx
│   │   ├── store/
│   │   │   ├── receiptStore.ts
│   │   │   ├── analyticsStore.ts
│   │   │   ├── chatStore.ts
│   │   │   └── settingsStore.ts
│   │   ├── lib/
│   │   │   ├── api.ts             # API client
│   │   │   ├── types.ts           # TypeScript types
│   │   │   └── utils.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   └── USER_GUIDE.md
│
├── docker-compose.yml              # Optional
└── .gitignore
```

---

## JSON Prompt dla Cursora

Użyj tego JSON'a bezpośrednio w Cursorze (Tools → Custom Prompt):

```json
{
  "project_name": "ParagonOCR Web Edition",
  "mode": "Full-stack development",
  "role": "Senior developer",
  "language": "Polish preferred for docs",
  
  "phase_1_setup": {
    "backend_modules": [
      "app/main.py - FastAPI initialization",
      "app/config.py - Environment configuration",
      "app/database.py - SQLAlchemy ORM models",
      "services/ocr_service.py - Tesseract wrapper",
      "services/llm_service.py - Ollama client",
      "services/rag_service.py - RAG engine"
    ],
    "frontend_pages": [
      "src/pages/Dashboard.tsx",
      "src/pages/Receipts.tsx",
      "src/components/ReceiptUploader.tsx",
      "src/components/ChatUI.tsx"
    ]
  },

  "code_tasks": [
    {
      "id": 1,
      "task": "OCR Service - Create a Python class that wraps Tesseract for PDF and image extraction"
    },
    {
      "id": 2,
      "task": "LLM Service - Build Ollama client for receipt parsing and chat with streaming"
    },
    {
      "id": 3,
      "task": "FastAPI Endpoints - Create POST /api/receipts/upload with WebSocket integration"
    },
    {
      "id": 4,
      "task": "React Component - Build ReceiptUploader with drag-drop and progress tracking"
    },
    {
      "id": 5,
      "task": "RAG Engine - Implement semantic search with sentence-transformers"
    }
  ]
}
```

---

## Roadmap Implementacji

### Phase 1: MVP (Weeks 1-2)
- [ ] Backend setup (FastAPI + SQLAlchemy)
- [ ] OCR service (Tesseract integration)
- [ ] LLM service (Ollama + prompts)
- [ ] Basic API endpoints
- [ ] Database schema + migrations
- [ ] Frontend setup (React + Vite)
- [ ] Receipt uploader component
- [ ] Basic dashboard

**Expected Result:** Upload receipt → OCR → LLM parsing → Display items

### Phase 2: Analytics & Intelligence (Weeks 3-4)
- [ ] Analytics service (spending patterns)
- [ ] RAG engine (semantic search)
- [ ] Product search & database
- [ ] Dashboard with charts
- [ ] Meal planner logic
- [ ] Shopping list generator

**Expected Result:** Full expense tracking + AI-powered suggestions

### Phase 3: Polish & Assistant (Weeks 5-6)
- [ ] Chat UI with streaming
- [ ] Advanced RAG (conversation memory)
- [ ] Settings & configuration
- [ ] Data export/import
- [ ] Performance optimization
- [ ] Testing & documentation

**Expected Result:** Fully functional personal AI assistant

---

## Key Features

### 📄 Receipt Processing
- Upload PDF, PNG, JPG, TIFF
- Automatic OCR (Tesseract)
- AI parsing (Bielik LLM)
- Product extraction & normalization
- Store data in SQLite

### 📊 Analytics Dashboard
- Daily/monthly spending
- Category breakdown
- Shop comparison
- Budget tracking
- Trend analysis

### 🤖 AI Assistant
- Local RAG-powered chat
- Meal suggestions
- Recipe recommendations
- Shopping optimization
- Food waste reduction

### 🛒 Smart Shopping
- Price history & comparison
- Auto-generated lists
- Product search
- Category management

---

## Prompts dla Ollama (Bielik)

```python
# Receipt Parsing Prompt
RECEIPT_PARSING_PROMPT = """
Jesteś ekspertem w przetwarzaniu paragonów. Analizuj tekst z paragonu i wyodrębnij:
1. Data i godzina
2. Nazwa sklepu
3. Lista produktów (nazwa, ilość, cena)
4. Podsumowanie (rabaty, podatek, suma)

Zwróć JSON: {"date": "...", "shop": "...", "items": [...], "total": ...}
"""

# Product Normalization
PRODUCT_NORM_PROMPT = """
Normalizuj nazwy produktów (usuń gramy, % zawartości, marki).
Zwróć JSON: {"original": "...", "normalized": "...", "category": "..."}
"""
```

---

## Troubleshooting

### Ollama Not Found
```bash
# Zainstaluj Ollama: https://ollama.ai
# Lub: brew install ollama (Mac)

# Sprawdź, czy działa:
curl http://localhost:11434/api/tags
```

### Tesseract Not Found
```bash
# Linux
sudo apt-get install tesseract-ocr

# Mac
brew install tesseract

# Windows: Download installer
# https://github.com/UB-Mannheim/tesseract/wiki
```

### Port Already in Use
```bash
# Backend
uvicorn app.main:app --reload --port 8001

# Frontend
npm run dev -- --port 5174
```

---

## Linki & Zasoby

- **Ollama:** https://ollama.ai
- **FastAPI:** https://fastapi.tiangolo.com
- **React:** https://react.dev
- **SQLAlchemy:** https://sqlalchemy.org
- **TailwindCSS:** https://tailwindcss.com

---

## Support & Contribution

Projekt jest aktywnie rozwijany. Struktura jest modularna i łatwa do rozszerzenia o nowe funkcje (np. rodzinne podziały wydatków, integracja z bankami, mobilna aplikacja).

---

**Ostatnia aktualizacja:** 7 grudnia 2025
**Wersja:** 1.0.0-beta (Landing Page & Real Data Integration)
