@echo off
echo Starting ParagonOCR...

:: Start Backend
start "ParagonOCR Backend" cmd /k "cd backend && call venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: Start Frontend
start "ParagonOCR Frontend" cmd /k "cd frontend && npm run dev"

echo Application started!
echo Frontend: http://localhost:5173
echo Backend: http://localhost:8000
pause
