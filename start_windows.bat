@echo off
TITLE ParagonOCR Launcher
CLS

ECHO ========================================================
ECHO    ParagonOCR - Uruchamianie Systemu (Windows Native)
ECHO ========================================================
ECHO.

:: 1. Sprawdzenie wymagań
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO [BLAD] Nie wykryto Python. Upewnij sie, ze jest w PATH.
    PAUSE
    EXIT /B
)

node --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO [BLAD] Nie wykryto Node.js. Upewnij sie, ze jest w PATH.
    PAUSE
    EXIT /B
)

:: 2. Backend Setup & Start
ECHO [1/2] Uruchamianie Backend...
CD backend

IF NOT EXIST "venv" (
    ECHO Tworzenie srodowiska wirtualnego venv...
    python -m venv venv
)

ECHO Aktywacja venv i instalacja zaleznosci...
CALL venv\Scripts\activate.bat
pip install -r requirements.txt >nul

:: Uruchomienie Backendu w nowym oknie
START "ParagonOCR Backend" cmd /k "venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"

CD ..

:: 3. Frontend Setup & Start
ECHO.
ECHO [2/2] Uruchamianie Frontend...
CD frontend

IF NOT EXIST "node_modules" (
    ECHO Instalacja zaleznosci Node...
    npm install
)

:: Uruchomienie Frontendu w nowym oknie
START "ParagonOCR Frontend" cmd /k "npm run dev"

CD ..

ECHO.
ECHO ========================================================
ECHO    SUKCES! Aplikacja startuje w nowych oknach.
ECHO    Frontend: http://localhost:5173
ECHO    Backend:  http://localhost:8000/docs
ECHO ========================================================
ECHO.
ECHO P.S. Jesli OCR PDF nie dziala, sprawdz czy masz 'poppler' w PATH!
PAUSE
