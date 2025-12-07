# 🏗️ ParagonOCR Web Edition - Architecture

## System Overview

ParagonOCR Web Edition is a full-stack web application for receipt processing, expense tracking, and AI-powered meal planning. The system uses a modern tech stack with FastAPI backend, React frontend, and local AI services.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React 19)                      │
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

## Component Architecture

### Frontend (React + TypeScript)

**Technology Stack:**
- **React 19.2** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Zustand** - State management
- **TailwindCSS** - Styling
- **Recharts** - Data visualization

**Structure:**
```
frontend/src/
├── pages/              # Page components
│   ├── Dashboard.tsx
│   ├── Receipts.tsx
│   ├── Products.tsx
│   ├── Analytics.tsx
│   ├── ShoppingList.tsx
│   └── Chat.tsx
├── components/         # Reusable components
│   ├── ReceiptUploader.tsx
│   ├── ReceiptViewer.tsx
│   ├── ChatUI.tsx
│   └── SpendingChart.tsx
├── store/              # Zustand stores
│   ├── receiptStore.ts
│   ├── analyticsStore.ts
│   └── chatStore.ts
├── lib/                # Utilities
│   ├── api.ts          # API client
│   ├── types.ts        # TypeScript types
│   └── utils.ts
└── main.tsx            # Entry point
```

### Backend (FastAPI)

**Technology Stack:**
- **FastAPI** - Web framework
- **SQLAlchemy 2.x** - ORM
- **SQLite** - Database (WAL mode)
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **SlowAPI** - Rate limiting

**Structure:**
```
backend/app/
├── main.py             # FastAPI app entry point
├── config.py           # Configuration (env vars)
├── database.py         # SQLAlchemy setup
├── schemas.py          # Pydantic models
├── dependencies.py     # FastAPI dependencies
├── models/             # SQLAlchemy models
│   ├── receipt.py
│   ├── product.py
│   ├── category.py
│   ├── shop.py
│   ├── user.py
│   ├── chat_history.py
│   └── shopping_list.py
├── routers/            # API routes
│   ├── receipts.py     # Receipt upload & processing
│   ├── products.py     # Product management
│   ├── chat.py         # AI chat endpoints
│   ├── analytics.py    # Analytics endpoints
│   └── auth.py         # Authentication
└── services/           # Business logic
    ├── ocr_service.py  # Tesseract OCR wrapper
    ├── llm_service.py  # Ollama client
    ├── rag_service.py  # RAG engine
    ├── analytics_service.py
    └── auth_service.py
```

## Data Flow

### Receipt Processing Flow

```
1. User uploads receipt (PDF/image)
   ↓
2. Frontend → POST /api/receipts/upload
   ↓
3. Backend saves file, creates Receipt record
   ↓
4. Background task starts:
   a. OCR Service extracts text (Tesseract)
   b. LLM Service parses receipt (Ollama)
   c. Products normalized and saved
   d. Receipt status updated
   ↓
5. WebSocket updates sent to frontend
   ↓
6. Frontend displays processed receipt
```

### Chat Flow

```
1. User sends message in Chat UI
   ↓
2. Frontend → POST /api/chat/messages
   ↓
3. RAG Service searches products/receipts
   ↓
4. LLM Service generates response (Ollama)
   ↓
5. Response streamed back to frontend
   ↓
6. Message saved to database
```

## Database Schema

See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for detailed entity-relationship diagrams.

**Core Entities:**
- **User** - Authentication and user data
- **Receipt** - Receipt metadata (date, shop, total)
- **ReceiptItem** - Individual items from receipts
- **Product** - Normalized product names
- **Category** - Product categories
- **Shop** - Store information
- **Conversation** - Chat conversation threads
- **Message** - Individual chat messages
- **ShoppingList** - Shopping list items

## External Services

### Ollama (Local LLM)
- **Purpose:** Receipt parsing, chat responses, RAG context
- **Model:** `SpeakLeash/bielik-11b-v2.3-instruct:Q4_K_M` (Polish)
- **Endpoint:** `http://localhost:11434`
- **Integration:** Async HTTP client in `llm_service.py`

### Tesseract OCR
- **Purpose:** Text extraction from images/PDFs
- **Integration:** Python wrapper via `pytesseract`
- **Configuration:** System-installed binary

### Sentence Transformers
- **Purpose:** Embeddings for semantic search (RAG)
- **Model:** Local model loaded on startup
- **Usage:** Product/receipt similarity search

## Security Architecture

### Authentication
- **OAuth2** with password flow
- **FIDO2 WebAuthn Passkeys** for passwordless authentication
- **JWT tokens** for API authentication
- **Rate limiting** on auth endpoints (5 requests/minute)
- **Challenge-based authentication** with 10-minute expiration

### Authorization
- All endpoints require authentication (except `/health`)
- User-scoped data access (users can only see their own receipts)

### Input Validation
- File size limits (configurable, default 10MB)
- File type validation (PDF, PNG, JPG, TIFF)
- Pydantic schemas for all API inputs

### Data Protection
- SQL injection protection (SQLAlchemy ORM)
- Path traversal protection (file path validation)
- XSS protection (React auto-escaping)

## Performance Optimizations

### Database
- **WAL mode** enabled for SQLite (better concurrency)
- **Composite indices** on frequently queried columns
- **Connection pooling** via SQLAlchemy

### API
- **GZip compression** for responses > 1KB
- **Async processing** for receipt uploads
- **WebSocket** for real-time updates

### Frontend
- **Code splitting** via Vite
- **Lazy loading** for routes
- **Optimistic updates** in Zustand stores

## Deployment Architecture

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

**Options:**
1. **Docker Compose** - Full stack in containers
2. **Manual Setup** - Backend + Frontend separately
3. **Production** - Nginx reverse proxy + Gunicorn

## Development Workflow

1. **Backend Development:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. **Frontend Development:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Database Migrations:**
   ```bash
   cd backend
   alembic revision --autogenerate -m "description"
   alembic upgrade head
   ```

## Testing Strategy

- **Backend:** pytest with async support
- **Frontend:** Vitest + React Testing Library
- **Integration:** End-to-end tests for critical flows
- **Coverage:** Target 80%+ code coverage

## Monitoring & Logging

- **Structured logging** via Python `logging` module
- **Request logging** in FastAPI middleware
- **Error tracking** (to be implemented)
- **Performance metrics** (to be implemented)

---

**Last Updated:** 2025-12-07  
**Version:** 1.0.0-beta

