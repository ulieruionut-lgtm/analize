@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

REM =============================================================================
REM  INSTALLER RAILWAY.APP - DEPLOYMENT AUTOMAT
REM  Pune aplicația online în 5 minute!
REM =============================================================================

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║        🚀 DEPLOYMENT RAILWAY.APP - INSTALLER AUTOMAT 🚀               ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo Acest script va:
echo   ✓ Verifica Node.js (pentru Railway CLI)
echo   ✓ Instala Railway CLI
echo   ✓ Initia Git repository
echo   ✓ Face deploy pe Railway.app
echo   ✓ Configura PostgreSQL database
echo   ✓ Rula migrările
echo.
pause

REM ─────────────────────────────────────────────────────────────────────────────
REM  Pas 1: Verificare Node.js
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  [1/7] Verificare Node.js...
echo ═══════════════════════════════════════════════════════════════════════════

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ✗ Node.js nu este instalat!
    echo.
    echo Instalarea Railway CLI necesită Node.js.
    echo.
    echo Opțiuni:
    echo   A) Instalează automat cu winget
    echo   B) Descarcă manual de la: https://nodejs.org
    echo   C) Anulează
    echo.
    choice /C ABC /N /M "Alege opțiunea (A/B/C): "
    
    if !errorlevel! EQU 1 (
        echo.
        echo → Instalez Node.js cu winget...
        winget install OpenJS.NodeJS.LTS
        if !errorlevel! neq 0 (
            echo ✗ Instalarea a eșuat. Instalează manual: https://nodejs.org
            pause
            exit /b 1
        )
        echo ✓ Node.js instalat cu succes!
        echo → Reîncearcă script-ul după ce închizi această fereastră.
        pause
        exit /b 0
    )
    
    if !errorlevel! EQU 2 (
        echo.
        echo → Deschid pagina de download Node.js...
        start https://nodejs.org
        echo → După instalare, reîncearcă acest script.
        pause
        exit /b 0
    )
    
    echo Anulat de utilizator.
    pause
    exit /b 0
)

for /f "tokens=*" %%v in ('node --version') do set NODE_VERSION=%%v
echo ✓ Node.js este instalat: !NODE_VERSION!

REM ─────────────────────────────────────────────────────────────────────────────
REM  Pas 2: Instalare Railway CLI
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  [2/7] Instalare Railway CLI...
echo ═══════════════════════════════════════════════════════════════════════════

where railway >nul 2>&1
if %errorlevel% neq 0 (
    echo → Railway CLI nu este instalat. Instalez...
    call npm install -g @railway/cli
    if !errorlevel! neq 0 (
        echo ✗ Instalarea Railway CLI a eșuat!
        pause
        exit /b 1
    )
    echo ✓ Railway CLI instalat cu succes!
) else (
    echo ✓ Railway CLI este deja instalat.
)

REM ─────────────────────────────────────────────────────────────────────────────
REM  Pas 3: Login Railway
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  [3/7] Login Railway.app...
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo → Se va deschide browserul pentru autentificare.
echo → După login, revino în această fereastră.
echo.
pause

railway whoami >nul 2>&1
if %errorlevel% neq 0 (
    echo → Autentificare Railway...
    call railway login
    if !errorlevel! neq 0 (
        echo ✗ Autentificarea a eșuat!
        pause
        exit /b 1
    )
)

for /f "tokens=*" %%u in ('railway whoami 2^>nul') do set RAILWAY_USER=%%u
if "!RAILWAY_USER!"=="" (
    echo ✗ Nu ești autentificat pe Railway!
    echo → Rulează: railway login
    pause
    exit /b 1
)
echo ✓ Autentificat ca: !RAILWAY_USER!

REM ─────────────────────────────────────────────────────────────────────────────
REM  Pas 4: Inițializare Git (dacă nu există)
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  [4/7] Inițializare Git repository...
echo ═══════════════════════════════════════════════════════════════════════════

if not exist ".git" (
    echo → Inițializez Git repository...
    git init
    git add .
    git commit -m "Initial commit - Aplicatie analize medicale"
    echo ✓ Git repository creat!
) else (
    echo ✓ Git repository deja existent.
    echo → Commit modificări recente...
    git add .
    git commit -m "Update pentru deployment Railway" 2>nul
    if !errorlevel! equ 0 (
        echo ✓ Modificări commituite.
    ) else (
        echo ℹ Nicio modificare de commitat.
    )
)

REM ─────────────────────────────────────────────────────────────────────────────
REM  Pas 5: Inițializare proiect Railway
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  [5/7] Creare proiect Railway...
echo ═══════════════════════════════════════════════════════════════════════════

railway status >nul 2>&1
if %errorlevel% neq 0 (
    echo → Creez proiect nou Railway...
    echo → Nume proiect: analize-medicale
    call railway init --name analize-medicale
    if !errorlevel! neq 0 (
        echo ✗ Crearea proiectului a eșuat!
        pause
        exit /b 1
    )
    echo ✓ Proiect Railway creat!
) else (
    echo ✓ Proiect Railway deja configurat.
)

REM ─────────────────────────────────────────────────────────────────────────────
REM  Pas 6: Adăugare PostgreSQL database
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  [6/7] Configurare PostgreSQL database...
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo ℹ Railway va crea automat variabila DATABASE_URL după ce adaugi PostgreSQL.
echo.
echo Pași manuali (în Railway dashboard):
echo   1. Click pe proiect
echo   2. Click "+ New" → "Database" → "PostgreSQL"
echo   3. Railway va genera automat DATABASE_URL
echo   4. După 30 secunde, continuă aici
echo.
echo → Deschid Railway dashboard...
call railway open
echo.
echo ⏳ Așteaptă 30 secunde ca database-ul să fie creat...
timeout /t 30 /nobreak
echo.

REM ─────────────────────────────────────────────────────────────────────────────
REM  Pas 7: Deploy aplicație
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  [7/7] Deploy aplicație pe Railway...
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo → Pornesc deployment (poate dura 2-3 minute)...
echo.
call railway up
if %errorlevel% neq 0 (
    echo.
    echo ✗ Deployment-ul a eșuat!
    echo.
    echo Verifică:
    echo   - Dashboard Railway pentru erori
    echo   - Logs: railway logs
    pause
    exit /b 1
)

echo.
echo ✓ Aplicația a fost deployed cu succes!

REM ─────────────────────────────────────────────────────────────────────────────
REM  Pas 8: Rulare migrații database
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  Rulare migrații database...
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo → Creez tabelele în PostgreSQL...
call railway run python run_migrations.py
if %errorlevel% neq 0 (
    echo.
    echo ⚠ Migrațiile au eșuat, dar aplicația poate funcționa.
    echo   Verifică DATABASE_URL în Railway dashboard.
    echo.
) else (
    echo ✓ Migrații executate cu succes!
)

REM ─────────────────────────────────────────────────────────────────────────────
REM  Finalizare
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                     🎉 DEPLOYMENT FINALIZAT! 🎉                       ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo ✓ Aplicația este LIVE pe Railway.app!
echo.
echo Comenzi utile:
echo   • Vezi URL-ul:        railway domain
echo   • Deschide app:       railway open
echo   • Vezi logs:          railway logs
echo   • Rulează comenzi:    railway run [command]
echo.
echo Următorii pași:
echo   1. Deschide aplicația: railway open
echo   2. Testează upload PDF
echo   3. Verifică interfața
echo   4. (Opțional) Adaugă domeniu custom în Railway settings
echo.

REM Obține și afișează URL-ul
echo → Obțin URL-ul aplicației...
for /f "tokens=*" %%u in ('railway domain 2^>nul') do set APP_URL=%%u
if not "!APP_URL!"=="" (
    echo.
    echo 🌐 URL aplicație: !APP_URL!
    echo.
    choice /C YN /N /M "Deschid aplicația în browser? (Y/N): "
    if !errorlevel! EQU 1 (
        start !APP_URL!
    )
)

echo.
echo Pentru suport:
echo   - Dashboard: railway open
echo   - Logs: railway logs --follow
echo   - Docs: https://docs.railway.app
echo.
pause
