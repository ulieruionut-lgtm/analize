@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

REM =============================================================================
REM  DEPLOYMENT 100%% RAILWAY - SIMPLU SI RAPID
REM  Pune aplicația online în 5 minute (fără Romarg)!
REM =============================================================================

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║        🚀 DEPLOYMENT 100%% RAILWAY - SUPER SIMPLU 🚀                  ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo Această variantă folosește DOAR Railway pentru TOTUL:
echo   ✓ Python + FastAPI (aplicația)
echo   ✓ PostgreSQL (database - GRATUIT inclus)
echo   ✓ HTTPS automat
echo   ✓ Zero configurări complexe
echo.
echo Timp estimat: 5 minute
echo Cost: GRATUIT (500h/lună)
echo.
pause

REM ─────────────────────────────────────────────────────────────────────────────
REM  PARTEA 1: Verificare și instalare Node.js
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  [1/5] Verificare Node.js...
echo ═══════════════════════════════════════════════════════════════════════════

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo X Node.js nu este instalat!
    echo.
    set /p install_node="Instalez Node.js automat cu winget? (Y/N): "
    if /i "!install_node!"=="Y" (
        echo.
        echo -^> Instalez Node.js...
        winget install OpenJS.NodeJS.LTS --silent
        if !errorlevel! neq 0 (
            echo X Instalarea a esuat!
            echo.
            echo Instalează manual de la: https://nodejs.org
            start https://nodejs.org
            pause
            exit /b 1
        )
        echo OK - Node.js instalat!
        echo.
        echo -^> Restart PowerShell-ul și reîncearcă acest script.
        pause
        exit /b 0
    ) else (
        echo.
        echo Instalează manual Node.js de la: https://nodejs.org
        start https://nodejs.org
        pause
        exit /b 0
    )
)

for /f "tokens=*" %%v in ('node --version') do set NODE_VERSION=%%v
echo OK - Node.js instalat: !NODE_VERSION!

REM ─────────────────────────────────────────────────────────────────────────────
REM  PARTEA 2: Instalare Railway CLI
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  [2/5] Instalare Railway CLI...
echo ═══════════════════════════════════════════════════════════════════════════

where railway >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo -^> Railway CLI nu este instalat. Instalez...
    call npm install -g @railway/cli
    if !errorlevel! neq 0 (
        echo X Instalarea Railway CLI a esuat!
        pause
        exit /b 1
    )
    echo OK - Railway CLI instalat!
) else (
    echo OK - Railway CLI deja instalat
)

REM ─────────────────────────────────────────────────────────────────────────────
REM  PARTEA 3: Login Railway
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  [3/5] Login Railway.app...
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo -^> Se va deschide browserul pentru autentificare.
echo -^> Creează cont GRATUIT cu GitHub, Google sau email.
echo -^> După login, revino în această fereastră.
echo.
pause

railway whoami >nul 2>&1
if %errorlevel% neq 0 (
    echo -^> Deschid Railway login...
    call railway login
    if !errorlevel! neq 0 (
        echo X Autentificarea a esuat!
        pause
        exit /b 1
    )
)

for /f "tokens=*" %%u in ('railway whoami 2^>nul') do set RAILWAY_USER=%%u
if "!RAILWAY_USER!"=="" (
    echo X Nu esti autentificat pe Railway!
    pause
    exit /b 1
)
echo OK - Autentificat ca: !RAILWAY_USER!

REM ─────────────────────────────────────────────────────────────────────────────
REM  PARTEA 4: Pregătire Git
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  [4/5] Pregătire cod...
echo ═══════════════════════════════════════════════════════════════════════════

if not exist ".git" (
    echo -^> Initializez Git repository...
    git init
    git add .
    git commit -m "Initial commit - Railway deployment"
    echo OK - Git repository creat!
) else (
    echo OK - Git repository existent
    echo -^> Commit modificari recente...
    git add .
    git commit -m "Update pentru Railway deployment" 2>nul
    if !errorlevel! equ 0 (
        echo OK - Modificari commituite
    ) else (
        echo i Nicio modificare noua
    )
)

REM ─────────────────────────────────────────────────────────────────────────────
REM  PARTEA 5: Deploy COMPLET pe Railway
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  [5/5] Deploy pe Railway...
echo ═══════════════════════════════════════════════════════════════════════════
echo.

railway status >nul 2>&1
if %errorlevel% neq 0 (
    echo -^> Creez proiect Railway nou...
    call railway init
    if !errorlevel! neq 0 (
        echo X Crearea proiectului a esuat!
        pause
        exit /b 1
    )
    echo OK - Proiect Railway creat!
) else (
    echo OK - Proiect Railway deja configurat
)

echo.
echo -^> Deploy aplicatie (2-3 minute)...
echo.
call railway up
if %errorlevel% neq 0 (
    echo.
    echo X Deployment-ul a esuat!
    echo.
    echo Verifica:
    echo   - Logs: railway logs
    echo   - Dashboard: railway open
    pause
    exit /b 1
)

echo.
echo OK - Aplicatia deployed!

echo.
echo -^> Adaug PostgreSQL database...
echo   (se va deschide Railway dashboard)
echo.
echo IMPORTANT: In Railway dashboard:
echo   1. Click pe proiectul tau
echo   2. Click "+ New" -^> "Database" -^> "PostgreSQL"
echo   3. Asteapta 30 secunde (database se creaza automat)
echo   4. DATABASE_URL se configureaza AUTOMAT!
echo.
echo -^> Deschid Railway dashboard...
call railway open
echo.
echo Ai adaugat PostgreSQL in Railway dashboard?
pause

echo.
echo -^> Rulez migratii database...
timeout /t 10 /nobreak >nul
call railway run python run_migrations.py
if %errorlevel% neq 0 (
    echo.
    echo ! Migratiile pot esua daca PostgreSQL nu e gata inca
    echo   Asteapta 30 secunde si incearca manual:
    echo   railway run python run_migrations.py
    echo.
) else (
    echo OK - Tabele create cu succes!
)

REM ─────────────────────────────────────────────────────────────────────────────
REM  FINALIZARE
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo -^> Obtin URL-ul aplicatiei...
for /f "tokens=*" %%u in ('railway domain 2^>nul') do set APP_URL=%%u

echo.
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                     🎉 DEPLOYMENT FINALIZAT! 🎉                       ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo OK - Aplicatia este LIVE pe Railway.app!
echo.

if not "!APP_URL!"=="" (
    echo 🌐 URL PUBLIC: !APP_URL!
    echo.
    echo Testeaza aplicatia:
    echo   • Health check: !APP_URL!/health
    echo   • Interfata:    !APP_URL!
    echo.
)

echo ✓ Python + FastAPI: Railway
echo ✓ PostgreSQL: Railway (GRATUIT)
echo ✓ HTTPS: Automat
echo ✓ Backup: Automat
echo ✓ Cost: 0 lei/luna (500h gratuit)
echo.
echo Comenzi utile:
echo   • Logs:       railway logs --follow
echo   • Restart:    railway up
echo   • Dashboard:  railway open
echo   • Variables:  railway variables
echo   • Shell:      railway shell
echo.

if not "!APP_URL!"=="" (
    set /p open_browser="Deschid aplicatia in browser? (Y/N): "
    if /i "!open_browser!"=="Y" (
        start !APP_URL!
    )
)

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  Succes! Aplicatia ta este 100%% pe Railway! 🚀
echo ═══════════════════════════════════════════════════════════════════════════
echo.
pause
