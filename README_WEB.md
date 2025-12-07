# ParagonOCR Web Edition

Modern web application for receipt processing and expense tracking with AI-powered parsing.

## Project Structure

```
ParagonOCR/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── main.py      # FastAPI app entry point
│   │   ├── config.py    # Configuration settings
│   │   ├── database.py  # Database setup
│   │   ├── models/      # SQLAlchemy models
│   │   ├── routers/     # API endpoints
│   │   └── services/    # Business logic (OCR, LLM)
│   ├── alembic/         # Database migrations
│   └── requirements.txt
│
└── frontend/            # React + TypeScript frontend
    ├── src/
    │   ├── components/  # React components
    │   ├── pages/       # Page components
    │   ├── store/       # Zustand stores
    │   └── lib/         # API client
    └── package.json
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- Ollama installed and running (with Bielik model)
- Tesseract OCR installed
- SQLite (included with Python)

## Backend Setup

1. **Create virtual environment:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

4. **Initialize database:**
```bash
# Run Alembic migrations
alembic upgrade head

# Or initialize directly
python -m app.main
```

5. **Start backend server:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at `http://localhost:8000`

## Frontend Setup

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Start development server:**
```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

## Features (Phase 1 - MVP)

✅ **Receipt Upload**
- Drag-and-drop file upload
- Support for PDF, PNG, JPG, TIFF
- Real-time progress indicators

✅ **OCR Processing**
- Tesseract OCR integration
- PDF to image conversion
- Image preprocessing

✅ **AI Parsing**
- Bielik LLM via Ollama
- Structured JSON extraction
- Product normalization

✅ **Dashboard**
- Recent receipts list
- Spending summary
- Quick statistics

✅ **Receipt Viewer**
- Detailed receipt display
- Item list with prices
- Shop and date information

## API Endpoints

- `POST /api/receipts/upload` - Upload and process receipt
- `GET /api/receipts` - List receipts (with filters)
- `GET /api/receipts/{id}` - Get receipt details
- `WS /api/receipts/ws/processing/{id}` - WebSocket for progress updates

## Development

### Backend
- Uses FastAPI with SQLAlchemy ORM
- Database migrations with Alembic
- Type hints throughout
- Error handling and logging

### Frontend
- React 18 with TypeScript
- TailwindCSS for styling
- Zustand for state management
- Axios for API calls

## Next Steps (Phase 2)

- [ ] Analytics dashboard with charts
- [ ] RAG engine for semantic search
- [ ] Product database with price history
- [ ] AI chat interface
- [ ] Meal planner & shopping suggestions

## Troubleshooting

**Ollama connection error:**
- Ensure Ollama is running: `ollama serve`
- Check OLLAMA_HOST in `.env`
- Verify Bielik model is installed: `ollama list`

**OCR errors:**
- Verify Tesseract is installed: `tesseract --version`
- Check TESSERACT_CMD in `.env` if using custom path

**Database errors:**
- Ensure `data/` directory exists
- Check DATABASE_URL in `.env`
- Run migrations: `alembic upgrade head`

## License

Same as main ParagonOCR project.

