@echo off
cd /d "%~dp0"
echo Starting startup script...

:: Check if Windows venv exists
if not exist "backend\venv\Scripts\activate.bat" (
    echo [WARNING] Virtual environment missing or invalid (Linux style?).
    echo [INFO] Automatically running setup.bat to fix environment...
    call setup.bat
    if errorlevel 1 (
        echo [ERROR] Setup failed! Cannot start application.
        pause
        exit /b 1
    )
    echo [INFO] Setup complete. Proceeding to launch...
)

powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
pause
