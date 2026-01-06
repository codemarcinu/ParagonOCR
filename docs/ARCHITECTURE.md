# ParagonOCR Architecture

## System Overview
ParagonOCR is a full-stack web application designed for receipt digitization, expense tracking, and smart meal planning. It leverages local AI models to ensure privacy.

## Components

### Frontend
- **Framework**: React 19 (Vite)
- **State Management**: Zustand
- **Styling**: TailwindCSS
- **Communication**: REST API + WebSocket (for real-time OCR progress)

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLite (with SQLAlchemy & Alembic)
- **Task Processing**: Background tasks for OCR and LLM processing

### AI Services (Local)
- **OCR Engine**: Tesseract OCR (with specialized image preprocessing)
- **LLM**: Ollama (running 'Bielik' or similar models) for:
  - Product normalization
  - Category classification
  - RAG (Retrieval Augmented Generation) for chat

## Data Flow

1. **Upload**: User uploads an image/PDF.
2. **Preprocessing**: Image is corrected (Upscaling, Adaptive Thresholding, Deskewing).
3. **OCR**: Tesseract extracts raw text.
4. **Parsing**:
   - Helper scripts parse date/total.
   - LLM extracts structured items (Name, Quantity, Price).
5. **Normalization**:
   - Product names are normalized (e.g., "MLEKO" -> "Mleko").
   - Categories are assigned.
6. **Storage**: Data is saved to SQLite.

## Directory Structure
- `backend/`: API and Core Logic
- `frontend/`: React UI
- `data/`: Local storage (DB, images)
- `scripts/`: Automation and Verification tools
