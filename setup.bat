@echo off
cd /d "%~dp0"
echo Running setup script...
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
pause
