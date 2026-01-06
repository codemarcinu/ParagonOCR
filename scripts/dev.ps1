# ParagonOCR Web Edition - Development Server Script (Windows PowerShell)

$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "Starting ParagonOCR Web Edition development servers..." -ForegroundColor Cyan
Write-Host ""

# Check if Ollama is running
try {
    Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -ErrorAction Stop | Out-Null
}
catch {
    Write-Host "Ollama doesn't seem to be running" -ForegroundColor Yellow
    Write-Host "   Start it with: ollama serve" -ForegroundColor Blue
    Write-Host ""
}

# Start backend
Write-Host "Starting backend server..."
$backendArgs = '-Command "cd backend; if (Test-Path venv\Scripts\Activate.ps1) { . venv\Scripts\Activate.ps1 } else { Write-Error ''Venv missing!''; exit 1 }; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"'
$backendProcess = Start-Process -FilePath "powershell" -ArgumentList $backendArgs -PassThru -NoNewWindow

# Wait a moment for backend to start
Start-Sleep -Seconds 2

# Start frontend
Write-Host "Starting frontend server..."
$frontendArgs = '-Command "cd frontend; npm run dev"'
$frontendProcess = Start-Process -FilePath "powershell" -ArgumentList $frontendArgs -PassThru -NoNewWindow

Write-Host ""
Write-Host "Servers started!" -ForegroundColor Green
Write-Host ""
Write-Host "Backend PID: $($backendProcess.Id)"
Write-Host "Frontend PID: $($frontendProcess.Id)"
Write-Host ""
Write-Host "Access:"
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop all servers"
Write-Host ""

try {
    # Keep script running
    while ($true) {
        Start-Sleep -Seconds 1
        if ($backendProcess.HasExited -or $frontendProcess.HasExited) {
            break
        }
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping servers..."
    Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendProcess.Id -ErrorAction SilentlyContinue
}
