@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

cls
echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║           🚀 DEPLOYMENT RAILWAY - START PROASPĂT 🚀                    ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.
echo Cont nou Railway: scanari.cabinet@gmail.com
echo Vom face totul PAS CU PAS, foarte DETALIAT!
echo.
pause

cd /d "%~dp0"

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo   PASUL 1/6: VERIFICARE RAILWAY CLI
echo ═══════════════════════════════════════════════════════════════════════════
echo.

where railway >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Railway CLI nu este instalat.
    echo.
    echo Instalez acum cu npm...
    echo (Aceasta poate dura 1-2 minute)
    echo.
    
    npm install -g @railway/cli
    
    if !errorlevel! neq 0 (
        echo.
        echo [X] EROARE: Instalarea a esuat!
        echo.
        echo Posibile cauze:
        echo - npm nu este instalat
        echo - Conexiune internet
        echo.
        echo Instaleaza Node.js de aici:
        echo https://nodejs.org/
        echo.
        pause
        exit /b 1
    )
    
    echo.
    echo [OK] Railway CLI instalat cu succes!
) else (
    echo [OK] Railway CLI deja instalat!
    railway --version
)

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo   PASUL 2/6: LOGOUT DIN CONTUL VECHI (daca exista)
echo ═══════════════════════════════════════════════════════════════════════════
echo.

railway whoami >nul 2>&1
if %errorlevel% equ 0 (
    echo [!] Esti logat cu un cont vechi.
    echo.
    echo Fac logout automat...
    railway logout 2>nul
    echo.
    echo [OK] Logout efectuat!
) else (
    echo [OK] Nu esti logat (perfect pentru start proaspat!)
)

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo   PASUL 3/6: LOGIN CU CONTUL NOU
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Va trebui sa te loghezi cu: scanari.cabinet@gmail.com
echo.
echo Ce se va intampla:
echo   1. Se va deschide o pagina in browser
echo   2. Vei fi intrebat sa te loghezi
echo   3. Foloseste emailul: scanari.cabinet@gmail.com
echo   4. Dupa login, inchide tab-ul si revino aici
echo.
echo Gata sa continui?
pause

echo.
echo Deschid pagina de login...
railway login --browserless

if %errorlevel% neq 0 (
    echo.
    echo [X] Login-ul a esuat!
    echo.
    echo Incearca manual:
    echo   1. Deschide terminal nou
    echo   2. Scrie: railway login --browserless
    echo   3. Urmeaza instructiunile
    echo.
    pause
    exit /b 1
)

echo.
echo Verific login...
for /f "tokens=*" %%u in ('railway whoami 2^>nul') do set RAILWAY_USER=%%u

if "!RAILWAY_USER!"=="" (
    echo [X] Login-ul nu a reusit!
    pause
    exit /b 1
)

echo.
echo [OK] Logat cu succes ca: !RAILWAY_USER!
echo.

echo ═══════════════════════════════════════════════════════════════════════════
echo   PASUL 4/6: CREARE PROIECT NOU
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Voi crea un proiect Railway nou pentru aplicatia ta.
echo.
echo Nume proiect: ionut-analize-medicale
echo.
pause

echo.
echo Creez proiect...
railway init --name ionut-analize-medicale

if %errorlevel% neq 0 (
    echo.
    echo [!] Proiectul nu s-a creat automat.
    echo Incerc metoda alternativa...
    echo.
    railway link
)

echo.
echo Verific proiect...
railway status

echo.
echo [OK] Proiect creat!
echo.

echo ═══════════════════════════════════════════════════════════════════════════
echo   PASUL 5/6: ADAUGARE POSTGRESQL
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo IMPORTANT: Trebuie sa adaugi PostgreSQL MANUAL in Railway Dashboard!
echo.
echo De ce? Pentru ca Railway CLI nu poate crea database-uri direct.
echo.
echo PASI EXACTI:
echo.
echo 1. Se va deschide Railway dashboard
echo 2. Vei vedea proiectul "ionut-analize-medicale"
echo 3. Click pe proiect (daca nu e deja deschis)
echo 4. Click butonul "+ New" (sus-dreapta, mov)
echo 5. Selecteaza "Database"
echo 6. Selecteaza "PostgreSQL"
echo 7. Asteapta 20-30 secunde (se va afisa "Postgres" cu buline verzi)
echo 8. GATA!
echo.
echo Deschid dashboard-ul...
pause

railway open

echo.
echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║  AI ADAUGAT POSTGRESQL?                                                 ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.
echo Verifica ca PostgreSQL apare in dashboard cu buline verzi "Online".
echo.
set /p pg_ready="Scrie DA cand PostgreSQL e gata: "

if /i not "!pg_ready!"=="DA" (
    echo.
    echo [!] Te rog adauga PostgreSQL mai intai!
    echo Apoi ruleaza din nou acest script de la Pasul 6.
    echo.
    pause
    exit /b 0
)

echo.
echo [OK] PostgreSQL adaugat!
echo.
echo Astept 10 secunde ca PostgreSQL sa porneasca complet...
timeout /t 10 /nobreak >nul

echo ═══════════════════════════════════════════════════════════════════════════
echo   PASUL 6/6: DEPLOY APLICATIE
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Acum deploy-ez aplicatia Python pe Railway.
echo Aceasta poate dura 2-3 minute.
echo.
pause

echo.
echo [1] Commit modificari Git (daca sunt)...
git add . 2>nul
git commit -m "Deploy fresh pe Railway" 2>nul

echo.
echo [2] Deploy aplicatie...
echo (Asteapta 2-3 minute...)
echo.

railway up --detach

if %errorlevel% neq 0 (
    echo.
    echo [!] Deploy a esuat!
    echo.
    echo Verifica logs:
    echo   railway logs
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Deploy pornit!
echo.
echo Astept 90 secunde ca aplicatia sa porneasca...
echo.
timeout /t 90 /nobreak

echo ═══════════════════════════════════════════════════════════════════════════
echo   PASUL 7/6 (BONUS): RULARE MIGRATII DATABASE
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Acum creez tabelele in PostgreSQL.
echo.

railway run python run_migrations.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Migratiile au esuat!
    echo Probabil PostgreSQL nu e inca gata.
    echo.
    echo Incearca din nou in 1 minut:
    echo   railway run python run_migrations.py
    echo.
) else (
    echo.
    echo [OK] Tabele create cu succes!
)

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo   TEST FINAL
echo ═══════════════════════════════════════════════════════════════════════════
echo.

echo Obtin URL aplicatie...
for /f "tokens=*" %%d in ('railway domain 2^>nul') do set APP_DOMAIN=%%d

if "!APP_DOMAIN!"=="" (
    echo [!] Nu am putut obtine URL-ul automat.
    echo.
    echo Verifica manual in Railway dashboard.
    railway open
    pause
    exit /b 0
)

set APP_URL=https://!APP_DOMAIN!

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║  URL APLICATIE: !APP_URL!
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

echo Test /health...
echo.
curl -s "!APP_URL!/health"

echo.
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Daca vezi:
echo   {"status":"ok","database":"connected"}
echo.
echo = SUCCESS! Aplicatia merge perfect! 🎉
echo.
echo Daca vezi doar "OK" sau eroare:
echo   - Mai asteapta 1 minut
echo   - Sau verifica logs: railway logs
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.

set /p open_app="Deschid aplicatia in browser? (Y/N): "
if /i "!open_app!"=="Y" (
    start !APP_URL!
)

echo.
echo COMENZI UTILE:
echo   railway open           (dashboard)
echo   railway logs           (vezi logs)
echo   railway restart        (restart aplicatie)
echo   railway variables      (vezi DATABASE_URL)
echo.
pause
