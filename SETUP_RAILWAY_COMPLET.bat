@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║        🔧 SETUP COMPLET RAILWAY - FIX DATABASE 🔧                     ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo Acest script va rezolva problema DATABASE!
echo.
echo Aplicatia ruleaza dar /health returneaza doar "OK"
echo Trebuie sa adaugam PostgreSQL!
echo.
pause

REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo [1/6] Verificare Railway CLI...
echo.

where railway >nul 2>&1
if %errorlevel% neq 0 (
    echo Railway CLI nu este instalat!
    echo.
    echo Instalez acum...
    call npm install -g @railway/cli
    if !errorlevel! neq 0 (
        echo.
        echo EROARE: Instalarea a esuat!
        pause
        exit /b 1
    )
    echo.
    echo OK - Railway CLI instalat!
) else (
    echo OK - Railway CLI gasit!
)

REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo [2/6] Login Railway...
echo.

railway whoami >nul 2>&1
if %errorlevel% neq 0 (
    echo Nu esti logat pe Railway.
    echo.
    echo -> Se va deschide browserul pentru login.
    echo -> Dupa login, revino aici.
    echo.
    pause
    
    railway login
    if !errorlevel! neq 0 (
        echo.
        echo EROARE: Login-ul a esuat!
        pause
        exit /b 1
    )
)

for /f "tokens=*" %%u in ('railway whoami 2^>nul') do set RAILWAY_USER=%%u
echo OK - Logat ca: !RAILWAY_USER!

REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo [3/6] Verificare DATABASE_URL...
echo.

railway variables | findstr /C:"DATABASE_URL" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ╔════════════════════════════════════════════════════════════════════════╗
    echo ║  POSTGRESQL NU ESTE ADAUGAT!                                          ║
    echo ╚════════════════════════════════════════════════════════════════════════╝
    echo.
    echo Trebuie sa adaugi PostgreSQL in Railway Dashboard!
    echo.
    echo PASI:
    echo   1. Se va deschide Railway dashboard
    echo   2. Click pe proiectul tau
    echo   3. Click "+ New" (sus-dreapta)
    echo   4. Selecteaza "Database"
    echo   5. Selecteaza "PostgreSQL"
    echo   6. Click "Add PostgreSQL"
    echo   7. Asteapta 30 secunde
    echo.
    echo -> Deschid Railway dashboard...
    pause
    
    railway open
    
    echo.
    echo Ai adaugat PostgreSQL in dashboard?
    echo.
    set /p added="Scrie DA cand ai terminat: "
    
    if /i not "!added!"=="DA" (
        echo.
        echo Te rog adauga PostgreSQL si apoi ruleaza din nou acest script!
        pause
        exit /b 0
    )
    
    echo.
    echo OK - Astept 30 secunde ca PostgreSQL sa porneasca...
    timeout /t 30 /nobreak
    
) else (
    echo OK - DATABASE_URL gasit!
)

REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo [4/6] Rulare migratii database...
echo.

railway run python run_migrations.py
if %errorlevel% neq 0 (
    echo.
    echo ATENTIE: Migratiile au esuat!
    echo Probabil PostgreSQL nu e gata inca.
    echo.
    echo Incearca din nou in 1 minut:
    echo   railway run python run_migrations.py
    echo.
) else (
    echo.
    echo OK - Tabele create cu succes!
)

REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo [5/6] Restart aplicatie...
echo.

railway up --detach
if %errorlevel% neq 0 (
    echo.
    echo Folosesc restart in schimb...
    railway restart
)

echo.
echo OK - Aplicatia se reporneste...
echo Astept 15 secunde...
timeout /t 15 /nobreak

REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo [6/6] Test final...
echo.

for /f "tokens=*" %%u in ('railway domain 2^>nul') do set APP_URL=%%u

if "!APP_URL!"=="" (
    echo Nu am putut obtine URL-ul automat.
    echo.
    set /p APP_URL="Te rog introdu URL-ul aplicatiei (ex: https://analize-xxx.railway.app): "
)

echo.
echo URL aplicatie: !APP_URL!
echo.
echo Test health check: !APP_URL!/health
echo.

curl -s "!APP_URL!/health"

echo.
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Ar trebui sa vezi:
echo   {"status":"ok","database":"connected"}
echo.
echo Daca vezi "connected" -> SUCCESS! Aplicatia merge perfect!
echo Daca vezi doar "OK" -> Mai asteapta 1 minut si incearca din nou
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.

set /p open_browser="Deschid aplicatia in browser? (Y/N): "
if /i "!open_browser!"=="Y" (
    start !APP_URL!
)

echo.
echo Comenzi utile:
echo   railway logs --follow     (vezi logs real-time)
echo   railway open              (deschide dashboard)
echo   railway variables         (vezi toate variabilele)
echo   railway restart           (restart aplicatie)
echo.
pause
