@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================
echo   DEPLOY - Actualizare cu Backup
echo ============================================
echo.

where railway >nul 2>&1
if %errorlevel% neq 0 (
    echo [EROARE] Railway CLI nu este instalat.
    echo Instaleaza: npm install -g @railway/cli
    pause
    exit /b 1
)

railway whoami >nul 2>&1
if %errorlevel% neq 0 (
    echo Nu esti logat pe Railway.
    echo.
    railway login
    if %errorlevel% neq 0 (
        echo Login esuat.
        pause
        exit /b 1
    )
)

echo Deploy in curs... (1-2 minute)
echo.
railway up --detach

if %errorlevel% neq 0 (
    echo.
    echo [ATENTIE] railway up a esuat.
    echo.
    echo Daca Railway e conectat la GitHub, fa PUSH la cod:
    echo   - Deschide GitHub Desktop sau git
    echo   - Commit si Push modificari
    echo   - Railway va face deploy automat
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Deploy trimis! Asteapta 1-2 minute.
echo.
echo Apoi deschide: https://ionut-analize-app-production.up.railway.app
echo Ca admin, vei vedea butonul "Export backup" langa "Iesire" in header.
echo.
pause
