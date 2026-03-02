@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

cls
echo.
echo ========================================================================
echo           DEPLOYMENT RAILWAY - START PROASPAT
echo ========================================================================
echo.
echo Cont nou Railway: scanari.cabinet@gmail.com
echo Vom face totul PAS CU PAS!
echo.
pause

cd /d "%~dp0"

echo.
echo ========================================================================
echo   PASUL 1: VERIFICARE RAILWAY CLI
echo ========================================================================
echo.

where railway >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Railway CLI nu este instalat.
    echo.
    echo Instalez acum cu npm...
    echo.
    
    npm install -g @railway/cli
    
    if !errorlevel! neq 0 (
        echo.
        echo [X] EROARE: Instalarea a esuat!
        echo.
        echo Instaleaza Node.js de aici: https://nodejs.org/
        echo.
        pause
        exit /b 1
    )
    
    echo.
    echo [OK] Railway CLI instalat!
) else (
    echo [OK] Railway CLI deja instalat!
    railway --version
)

echo.
echo ========================================================================
echo   PASUL 2: LOGOUT DIN CONTUL VECHI
echo ========================================================================
echo.

railway whoami >nul 2>&1
if %errorlevel% equ 0 (
    echo [!] Esti logat cu un cont vechi.
    echo.
    echo Fac logout...
    railway logout 2>nul
    echo.
    echo [OK] Logout efectuat!
) else (
    echo [OK] Nu esti logat (perfect!)
)

echo.
echo ========================================================================
echo   PASUL 3: LOGIN CU CONTUL NOU
echo ========================================================================
echo.
echo Va trebui sa te loghezi cu: scanari.cabinet@gmail.com
echo.
echo Ce se va intampla:
echo   1. Vei primi un LINK in consola
echo   2. Click pe link (sau copiaza-l in browser)
echo   3. Loghează-te cu emailul: scanari.cabinet@gmail.com
echo   4. Dupa login, inchide tab-ul si revino aici
echo.
pause

echo.
echo Pornesc login...
railway login --browserless

if %errorlevel% neq 0 (
    echo.
    echo [X] Login-ul a esuat!
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
echo [OK] Logat ca: !RAILWAY_USER!

echo.
echo ========================================================================
echo   PASUL 4: CREARE PROIECT NOU
echo ========================================================================
echo.
pause

echo.
echo Creez proiect...
railway init

if %errorlevel% neq 0 (
    echo.
    echo [!] Incerc metoda alternativa...
    railway link
)

echo.
railway status

echo.
echo [OK] Proiect creat!

echo.
echo ========================================================================
echo   PASUL 5: ADAUGARE POSTGRESQL
echo ========================================================================
echo.
echo IMPORTANT: Trebuie sa adaugi PostgreSQL MANUAL in Railway Dashboard!
echo.
echo PASI:
echo   1. Se va deschide Railway dashboard
echo   2. Click pe proiectul tau
echo   3. Click "+ New" (sus-dreapta)
echo   4. Selecteaza "Database"
echo   5. Selecteaza "PostgreSQL"
echo   6. Asteapta 20-30 secunde
echo.
echo Deschid dashboard...
pause

railway open

echo.
echo.
echo AI ADAUGAT POSTGRESQL?
echo.
set /p pg_ready="Scrie DA cand PostgreSQL e gata: "

if /i not "!pg_ready!"=="DA" (
    echo.
    echo [!] Te rog adauga PostgreSQL!
    echo Apoi ruleaza din nou acest script.
    pause
    exit /b 0
)

echo.
echo [OK] PostgreSQL adaugat!
echo.
echo Astept 10 secunde...
timeout /t 10 /nobreak >nul

echo.
echo ========================================================================
echo   PASUL 6: DEPLOY APLICATIE
echo ========================================================================
echo.
pause

echo.
echo Commit modificari Git...
git add . 2>nul
git commit -m "Deploy fresh pe Railway" 2>nul

echo.
echo Deploy aplicatie (asteapta 2-3 minute)...
echo.

railway up --detach

if %errorlevel% neq 0 (
    echo.
    echo [!] Deploy a esuat!
    echo Verifica logs: railway logs
    pause
    exit /b 1
)

echo.
echo [OK] Deploy pornit!
echo.
echo Astept 90 secunde ca aplicatia sa porneasca...
timeout /t 90 /nobreak

echo.
echo ========================================================================
echo   PASUL 7: RULARE MIGRATII
echo ========================================================================
echo.

railway run python run_migrations.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Migratiile au esuat!
    echo.
    echo Incearca din nou:
    echo   railway run python run_migrations.py
    echo.
) else (
    echo.
    echo [OK] Tabele create!
)

echo.
echo ========================================================================
echo   TEST FINAL
echo ========================================================================
echo.

for /f "tokens=*" %%d in ('railway domain 2^>nul') do set APP_DOMAIN=%%d

if "!APP_DOMAIN!"=="" (
    echo [!] Nu am putut obtine URL-ul.
    railway open
    pause
    exit /b 0
)

set APP_URL=https://!APP_DOMAIN!

echo.
echo URL APLICATIE: !APP_URL!
echo.

echo Test /health...
echo.
curl -s "!APP_URL!/health"

echo.
echo.
echo Daca vezi: {"status":"ok","database":"connected"}
echo = SUCCESS!
echo.
echo Daca vezi doar "OK" = Mai asteapta 1 minut
echo.

set /p open_app="Deschid aplicatia in browser? (Y/N): "
if /i "!open_app!"=="Y" (
    start !APP_URL!
)

echo.
echo COMENZI UTILE:
echo   railway open
echo   railway logs
echo   railway restart
echo   railway variables
echo.
pause
