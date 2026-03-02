@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

cls
echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║              VERIFICARE SI FINALIZARE RAILWAY                           ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [INFO] Dashboard Railway:
echo https://railway.com/project/8a6b04fc-a7b8-4584-bcfc-5a47a83595a1
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo AI ADAUGAT POSTGRESQL IN DASHBOARD?
echo.
echo Daca nu:
echo   1. Deschide link-ul de mai sus
echo   2. Click '+ New' -^> 'Database' -^> 'PostgreSQL'
echo   3. Asteapta 30 secunde
echo.
echo Daca da, apasa orice tasta pentru a continua...
pause >nul

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo [PASUL 1] Verific conexiunea Railway...
echo.

railway whoami >nul 2>&1
if errorlevel 1 (
    echo X Nu esti logat in Railway!
    echo Ruleaza: railway login --browserless
    pause
    exit /b 1
)

echo OK - Logat in Railway
echo.

echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo [PASUL 2] Testez aplicatia INAINTE de migratii...
echo.

set APP_URL=https://zestful-truth-production-ae3e.up.railway.app

curl -s -m 10 "%APP_URL%/health" 2>nul
echo.

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo OPTIUNI:
echo.
echo [1] Ruleaza migratii PostgreSQL (daca ai adaugat PostgreSQL)
echo [2] Doar restart aplicatie
echo [3] Test aplicatie (fara schimbari)
echo [4] Iesire
echo.
set /p CHOICE="Alege optiunea (1-4): "

if "%CHOICE%"=="1" goto MIGRATIONS
if "%CHOICE%"=="2" goto RESTART
if "%CHOICE%"=="3" goto TEST
if "%CHOICE%"=="4" goto END

:MIGRATIONS
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo [MIGRATII] Rulez migratii PostgreSQL...
echo.
echo IMPORTANT: Daca vezi eroare "Multiple services", trebuie sa:
echo 1. Deschizi dashboard Railway
echo 2. Click pe serviciul aplicatiei
echo 3. Settings -^> Variables -^> Verifica DATABASE_URL
echo.

railway run python run_migrations.py

if errorlevel 1 (
    echo.
    echo X Migratiile au esuat!
    echo.
    echo Posibile cauze:
    echo - PostgreSQL nu e adaugat
    echo - Service-ul nu e conectat
    echo.
    echo Consulta: GHID_FINALIZARE_RAILWAY.txt
    echo.
    pause
    goto END
)

echo.
echo OK - Migratii executate cu succes!
goto RESTART

:RESTART
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo [RESTART] Repornesc aplicatia...
echo.

railway restart

echo.
echo Astept 60 secunde ca aplicatia sa porneasca...
timeout /t 60 /nobreak >nul

goto TEST

:TEST
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo [TEST] Testez aplicatia...
echo.
echo URL: %APP_URL%
echo.

echo Testez /health:
curl -s -m 15 "%APP_URL%/health"
echo.
echo.

echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Daca vezi JSON cu "database":"connected" = SUCCESS!
echo.
echo Daca nu merge, verifica Logs in Railway dashboard.
echo.

:END
echo.
pause
