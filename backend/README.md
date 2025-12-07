# ParagonOCR Web Edition - Backend

FastAPI backend for receipt processing and expense tracking.

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Initialize database:**
```bash
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

4. **Run server:**
```bash
uvicorn app.main:app --reload
```

## Project Structure

- `app/main.py` - FastAPI application entry point
- `app/config.py` - Configuration settings (Pydantic)
- `app/database.py` - SQLAlchemy setup and session management
- `app/models/` - SQLAlchemy ORM models
- `app/routers/` - API route handlers
- `app/services/` - Business logic (OCR, LLM)

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `OLLAMA_HOST` - Ollama server URL (default: http://localhost:11434)
- `TEXT_MODEL` - LLM model for parsing (default: bielik-4.5b-v3.0-instruct:Q4_K_M)
- `OCR_ENGINE` - OCR engine: 'tesseract' or 'easyocr'
- `DATABASE_URL` - SQLite database path

