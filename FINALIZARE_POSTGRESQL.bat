@echo off
chcp 65001 >nul 2>&1

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║           FINALIZARE DEPLOYMENT CU POSTGRESQL                           ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo URL Proiect Railway:
echo https://railway.com/project/8a6b04fc-a7b8-4584-bcfc-5a47a83595a1
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo PASII PE CARE TREBUIE SA-I FACI:
echo.
echo 1. Deschide link-ul de mai sus in browser
echo 2. Click '+ New' -^> 'Database' -^> 'PostgreSQL'
echo 3. Asteapta 30 secunde ca PostgreSQL sa porneasca
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Ai adaugat PostgreSQL in dashboard?
pause

echo.
echo [1/3] Rulez migratii PostgreSQL...
echo.
railway run python run_migrations.py

if errorlevel 1 (
    echo.
    echo X Migratiile au esuat!
    echo Verifica ca PostgreSQL e adaugat in dashboard.
    pause
    exit /b 1
)

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.

echo [2/3] Restart aplicatie...
railway restart

echo.
echo [3/3] Astept 45 secunde ca aplicatia sa porneasca...
timeout /t 45 /nobreak >nul

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.

echo [TEST] Verific aplicatia...
echo.

for /f "tokens=*" %%A in ('railway domain 2^>nul') do set APP_URL=%%A

if not "!APP_URL!"=="" (
    echo URL: !APP_URL!
    echo.
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
    echo X Nu am putut obtine URL-ul
)

pause
