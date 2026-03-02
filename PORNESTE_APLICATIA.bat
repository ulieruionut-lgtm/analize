@echo off
chcp 65001 >nul
title Analize medicale - Server
cd /d "%~dp0"

echo.
echo ========================================
echo   Pornire aplicatie Analize medicale
echo ========================================
echo.

REM Opreste orice server vechi pe portul 8000 (evita rularea codului vechi)
echo Oprire server vechi (daca exista)...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>nul
)
timeout /t 1 >nul

REM Verifica Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [EROARE] Python nu este instalat sau nu este in PATH.
    echo Instaleaza Python de la: https://www.python.org/downloads/
    echo La instalare, bifeaza "Add Python to PATH".
    pause
    exit /b 1
)

REM Creeaza venv daca nu exista
if not exist "venv\Scripts\python.exe" (
    echo Creare mediu virtual...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [EROARE] Nu s-a putut crea venv.
        pause
        exit /b 1
    )
    echo Mediu creat.
    echo.
)

REM Instalare pachete
echo Instalare / actualizare pachete...
"venv\Scripts\python.exe" -m pip install -q --upgrade pip
"venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    echo [EROARE] Instalare pachete esuata.
    pause
    exit /b 1
)
echo Pachete OK.
echo.

REM DATABASE_URL obligatoriu (PostgreSQL). Foloseste railway run sau .env
where railway >nul 2>nul
if %errorlevel% equ 0 (
    set USE_RAILWAY=1
) else (
    set USE_RAILWAY=0
    echo [INFO] Railway CLI negasit - ruleaza fara. DATABASE_URL trebuie sa fie in .env
    echo.
)

REM Migrari PostgreSQL
echo Pregatire baza de date (PostgreSQL)...
if %USE_RAILWAY% equ 1 (
    railway run "venv\Scripts\python.exe" run_migrations.py
) else (
    "venv\Scripts\python.exe" run_migrations.py
)
if %errorlevel% neq 0 (
    echo [EROARE] Migrari esuate. Ruleaza cu 'railway run' sau seteaza DATABASE_URL in .env
    pause
    exit /b 1
)
echo.

echo Pornire server (PostgreSQL)...
echo   Deschide:  http://localhost:8000
echo   Opreste:   Ctrl+C
echo ========================================
echo.

set "PATH=%PATH%;C:\Program Files\Tesseract-OCR"

cd backend
if %USE_RAILWAY% equ 1 (
    railway run "..\venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
) else (
    "..\venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
)
cd ..
pause
