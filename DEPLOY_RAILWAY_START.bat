@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

REM =============================================================================
REM  DEPLOYMENT RAILWAY.APP - GHID PAS CU PAS
REM  Pune aplicația online în 10 minute!
REM =============================================================================

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║        🚀 DEPLOYMENT RAILWAY.APP - STARTER 🚀                         ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo Acest ghid te va ajuta să pui aplicația online pe Railway.app
echo.
echo Ce vei face:
echo   1. Setup MySQL pe Romarg (via browser)
echo   2. Instalare Railway CLI (automat)
echo   3. Deploy aplicația (3 comenzi)
echo   4. Test final
echo.
echo Timp estimat: 10 minute
echo.
pause

REM ─────────────────────────────────────────────────────────────────────────────
REM  PARTEA 1: Setup MySQL pe Romarg
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  📋 PARTEA 1: Setup MySQL pe Romarg (3 minute)
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Înainte de a deploy pe Railway, trebuie să configurezi MySQL pe Romarg.
echo.
echo → Deschid cPanel Romarg în browser...
start https://cpanel.romarg.ro
echo.
echo Pași în cPanel:
echo.
echo 1. Login cu datele tale Romarg
echo.
echo 2. Găsește secțiunea "DATABASES" → Click pe "MySQL® Databases"
echo.
echo 3. CREEAZĂ DATABASE:
echo    - Secțiunea "Create New Database"
echo    - Nume database: analize
echo    - Click "Create Database"
echo.
echo 4. CREEAZĂ USER:
echo    - Secțiunea "MySQL Users" → "Add New User"
echo    - Username: analize_user
echo    - Password: [generează parolă puternică - salvează-o!]
echo    - Click "Create User"
echo.
echo 5. ASOCIAZĂ USER CU DATABASE:
echo    - Secțiunea "Add User To Database"
echo    - User: analize_user
echo    - Database: analize
echo    - Click "Add"
echo    - Pe pagina următoare: bifează "ALL PRIVILEGES"
echo    - Click "Make Changes"
echo.
echo 6. PERMITE ACCES REMOTE:
echo    - Înapoi la cPanel → găsește "Remote MySQL®"
echo    - În "Host" adaugă: %%.railway.internal
echo    - Click "Add Host"
echo    - Adaugă și: %%
echo    - Click "Add Host"
echo.
echo 7. TEST CONEXIUNE (opțional dar recomandat):
echo    - Upload deployment_cpanel.zip în File Manager
echo    - Extract arhiva
echo    - Accesează: http://your-domain.ro/installer.php
echo    - Completează datele MySQL și testează conexiunea
echo    - Click "Creează Tabelele MySQL"
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
set /p mysql_ready="Ai terminat setup-ul MySQL pe Romarg? (Y/N): "
if /i not "%mysql_ready%"=="Y" (
    echo.
    echo Termină mai întâi setup-ul MySQL, apoi revino și rulează acest script.
    pause
    exit /b 0
)

echo.
echo Perfect! Hai să notăm datele MySQL pentru Railway...
echo.

set /p mysql_host="Host MySQL (ex: cpanel.mysql.romarg.ro sau localhost): "
set /p mysql_db="Nume Database (ex: analize): "
set /p mysql_user="Username MySQL (ex: analize_user): "
set /p mysql_pass="Password MySQL: "

echo.
echo ✓ Date MySQL notate!
echo.
echo DATABASE_URL va fi:
echo mysql://%mysql_user%:%mysql_pass%@%mysql_host%:3306/%mysql_db%
echo.
pause

REM ─────────────────────────────────────────────────────────────────────────────
REM  PARTEA 2: Instalare Node.js și Railway CLI
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  📦 PARTEA 2: Instalare Railway CLI
echo ═══════════════════════════════════════════════════════════════════════════
echo.

REM Verificare Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Node.js nu este instalat!
    echo.
    echo Railway CLI necesită Node.js.
    echo.
    set /p install_node="Instalez Node.js automat cu winget? (Y/N): "
    if /i "!install_node!"=="Y" (
        echo.
        echo → Instalez Node.js...
        winget install OpenJS.NodeJS.LTS --silent
        if !errorlevel! neq 0 (
            echo ✗ Instalarea a eșuat!
            echo.
            echo Instalează manual de la: https://nodejs.org
            start https://nodejs.org
            pause
            exit /b 1
        )
        echo ✓ Node.js instalat!
        echo.
        echo → Reîncearcă acest script după ce închizi PowerShell-ul.
        pause
        exit /b 0
    ) else (
        echo.
        echo Instalează manual Node.js de la: https://nodejs.org
        start https://nodejs.org
        echo Apoi reîncearcă acest script.
        pause
        exit /b 0
    )
)

for /f "tokens=*" %%v in ('node --version') do set NODE_VERSION=%%v
echo ✓ Node.js instalat: !NODE_VERSION!

REM Verificare Railway CLI
where railway >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo → Railway CLI nu este instalat. Instalez...
    call npm install -g @railway/cli
    if !errorlevel! neq 0 (
        echo ✗ Instalarea Railway CLI a eșuat!
        pause
        exit /b 1
    )
    echo ✓ Railway CLI instalat!
) else (
    echo ✓ Railway CLI deja instalat
)

REM ─────────────────────────────────────────────────────────────────────────────
REM  PARTEA 3: Login Railway
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  🔐 PARTEA 3: Login Railway.app
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo → Se va deschide browserul pentru autentificare Railway.
echo → Creează cont GRATUIT (cu GitHub, Google, sau email)
echo → După login, revino în această fereastră.
echo.
pause

railway whoami >nul 2>&1
if %errorlevel% neq 0 (
    echo → Deschid Railway login...
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
REM  PARTEA 4: Pregătire Git
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  📂 PARTEA 4: Pregătire repository
echo ═══════════════════════════════════════════════════════════════════════════
echo.

if not exist ".git" (
    echo → Inițializez Git repository...
    git init
    git add .
    git commit -m "Initial commit - Deployment Railway"
    echo ✓ Git repository creat!
) else (
    echo ✓ Git repository existent
    echo → Commit modificări recente...
    git add .
    git commit -m "Update pentru deployment Railway" 2>nul
    if !errorlevel! equ 0 (
        echo ✓ Modificări commituite
    ) else (
        echo ℹ Nicio modificare nouă
    )
)

REM ─────────────────────────────────────────────────────────────────────────────
REM  PARTEA 5: Deploy pe Railway
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  🚀 PARTEA 5: Deploy aplicație pe Railway
echo ═══════════════════════════════════════════════════════════════════════════
echo.

railway status >nul 2>&1
if %errorlevel% neq 0 (
    echo → Creez proiect Railway nou...
    call railway init
    if !errorlevel! neq 0 (
        echo ✗ Crearea proiectului a eșuat!
        pause
        exit /b 1
    )
    echo ✓ Proiect Railway creat!
) else (
    echo ✓ Proiect Railway deja configurat
)

echo.
echo → Configurez DATABASE_URL...
set DB_URL=mysql://%mysql_user%:%mysql_pass%@%mysql_host%:3306/%mysql_db%
call railway variables set DATABASE_URL="%DB_URL%"
if !errorlevel! neq 0 (
    echo ⚠ Eroare la setarea DATABASE_URL
    echo Poți seta manual în Railway dashboard
) else (
    echo ✓ DATABASE_URL configurat!
)

echo.
echo → Pornesc deployment (poate dura 2-3 minute)...
echo   (Railway va construi și porni aplicația)
echo.
call railway up
if %errorlevel% neq 0 (
    echo.
    echo ✗ Deployment-ul a eșuat!
    echo.
    echo Verifică:
    echo   - Logs în Railway dashboard
    echo   - Comanda: railway logs
    pause
    exit /b 1
)

echo.
echo ✓ Aplicația a fost deployed cu succes!

REM ─────────────────────────────────────────────────────────────────────────────
REM  PARTEA 6: Obținere URL și test
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  🌐 PARTEA 6: Obținere URL public
echo ═══════════════════════════════════════════════════════════════════════════
echo.

echo → Obțin URL-ul aplicației...
for /f "tokens=*" %%u in ('railway domain 2^>nul') do set APP_URL=%%u
if "!APP_URL!"=="" (
    echo ⚠ Nu s-a putut obține URL-ul automat
    echo.
    echo Rulează manual: railway domain
    echo Sau verifică în Railway dashboard
) else (
    echo.
    echo ✓ URL aplicație: !APP_URL!
    echo.
)

echo ═══════════════════════════════════════════════════════════════════════════
echo  🧪 TEST APLICAȚIE
echo ═══════════════════════════════════════════════════════════════════════════
echo.

if not "!APP_URL!"=="" (
    echo → Test health check...
    timeout /t 5 /nobreak >nul
    
    curl -s "!APP_URL!/health" >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✓ Aplicația răspunde!
        echo.
        echo Test detaliat: !APP_URL!/health
        curl "!APP_URL!/health"
    ) else (
        echo ⚠ Aplicația nu răspunde încă (poate mai necesită câteva secunde)
        echo.
        echo Verifică manual: !APP_URL!/health
    )
)

REM ─────────────────────────────────────────────────────────────────────────────
REM  FINALIZARE
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                     🎉 DEPLOYMENT FINALIZAT! 🎉                       ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo ✓ Aplicația este LIVE pe Railway.app!
echo.

if not "!APP_URL!"=="" (
    echo 🌐 URL PUBLIC: !APP_URL!
    echo.
    echo Testează aplicația:
    echo   • Health check: !APP_URL!/health
    echo   • Interfață:    !APP_URL!
    echo.
)

echo Comenzi utile Railway:
echo   • Vezi logs:          railway logs
echo   • Logs real-time:     railway logs --follow
echo   • Restart app:        railway up
echo   • Deschide dashboard: railway open
echo   • Vezi variabile:     railway variables
echo   • Conectare SSH:      railway shell
echo.
echo Următorii pași:
echo   1. Accesează aplicația în browser
echo   2. Testează upload PDF
echo   3. Verifică că datele apar în MySQL (pe Romarg)
echo   4. (Opțional) Configurează domeniu custom în Railway dashboard
echo.

if not "!APP_URL!"=="" (
    set /p open_browser="Deschid aplicația în browser? (Y/N): "
    if /i "!open_browser!"=="Y" (
        start !APP_URL!
    )
)

echo.
echo 📚 Documentație:
echo   • Railway Docs: https://docs.railway.app
echo   • Dashboard: railway open
echo   • Support: https://railway.app/discord
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  Succes! Aplicația ta este acum ONLINE! 🚀
echo ═══════════════════════════════════════════════════════════════════════════
echo.
pause
