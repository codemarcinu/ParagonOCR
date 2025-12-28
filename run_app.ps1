Write-Host "Starting ParagonOCR..." -ForegroundColor Green

# Start Backend
Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd backend && call venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -WindowStyle Normal

# Start Frontend
Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd frontend && npm run dev" -WindowStyle Normal

Write-Host "Application started!" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173"
Write-Host "Backend: http://localhost:8000"
Read-Host -Prompt "Press Enter to exit launcher"
