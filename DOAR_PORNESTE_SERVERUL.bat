@echo off
chcp 65001 >nul
title Analize medicale - Server
cd /d "%~dp0"

REM Opreste server vechi pe portul 8000
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>nul
)
timeout /t 1 >nul

if not exist "venv\Scripts\python.exe" (
    echo [EROARE] Ruleaza mai intai: PORNESTE_APLICATIA.bat
    pause
    exit /b 1
)

echo Pornire server...
echo Deschide:  http://localhost:8000
echo Opreste:   Ctrl+C
echo.

REM Adauga Tesseract in PATH (pentru OCR fisiere scanate)
set "PATH=%PATH%;C:\Program Files\Tesseract-OCR"

cd backend
"..\venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
cd ..
pause
