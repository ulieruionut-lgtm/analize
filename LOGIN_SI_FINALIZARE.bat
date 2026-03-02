@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║           LOGIN RAILWAY + FINALIZARE POSTGRESQL                         ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [PASUL 1] Login Railway...
echo.
echo Se va deschide browserul.
echo Autorizeaza aplicatia si inchide tab-ul.
echo.
pause

railway login --browserless

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.

echo [PASUL 2] Rulare migratii PostgreSQL...
echo.
railway run python run_migrations.py

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.

echo [PASUL 3] Restart aplicatie...
railway restart

echo.
echo [PASUL 4] Astept 60 secunde ca aplicatia sa porneasca...
timeout /t 60 /nobreak >nul

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.

echo [PASUL 5] Obtin URL aplicatie...
echo.
for /f "tokens=*" %%A in ('railway domain 2^>nul') do set DOMAIN=%%A

if not "!DOMAIN!"=="" (
    set APP_URL=https://!DOMAIN!
    echo URL: !APP_URL!
    echo.
    
    echo Test /health:
    curl -s "!APP_URL!/health"
    echo.
    echo.
    echo ╔══════════════════════════════════════════════════════════════════════════╗
    echo ║                    🎉 DEPLOYMENT FINALIZAT! 🎉                          ║
    echo ╚══════════════════════════════════════════════════════════════════════════╝
    echo.
    echo Aplicatia ta: !APP_URL!
    echo.
) else (
    echo X Nu am putut obtine URL-ul.
    echo Verifica: railway domain
)

echo.
pause
