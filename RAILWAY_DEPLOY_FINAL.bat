@echo off
chcp 65001 >nul

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║           🚀 RAILWAY DEPLOYMENT - FINAL SIMPLU 🚀                     ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo Acest script te va loga pe Railway si va face deploy cu SQLite!
echo.
echo SQLite = fara PostgreSQL, merge imediat!
echo (Datele se resetează la redeploy, dar pentru test merge perfect!)
echo.
pause

echo.
echo [1/5] Login Railway...
echo.
echo Se va deschide browserul.
echo Logheaz-te cu GitHub, Google sau Email.
echo Dupa login, apasa Enter aici.
echo.
pause

railway login

if %errorlevel% neq 0 (
    echo.
    echo EROARE: Login esuat!
    pause
    exit /b 1
)

echo.
echo OK - Verificare login...
railway whoami

echo.
echo [2/5] Verificare/Creare proiect...
echo.

railway status >nul 2>&1
if %errorlevel% neq 0 (
    echo Creez proiect nou...
    railway init
) else (
    echo OK - Proiect existent!
)

echo.
echo [3/5] Commit modificari (SQLite config)...
echo.

git add .
git commit -m "Deploy Railway cu SQLite"

echo.
echo [4/5] Deploy pe Railway (2-3 minute)...
echo.
echo Aplicatia va folosi SQLite (fara PostgreSQL)!
echo Asteapta pana se termina...
echo.

railway up

if %errorlevel% neq 0 (
    echo.
    echo EROARE: Deployment esuat!
    echo.
    echo Vezi logs: railway logs
    pause
    exit /b 1
)

echo.
echo OK - Deployment finalizat!

echo.
echo [5/5] Test aplicatie...
echo.
echo Astept 30 secunde ca aplicatia sa porneasca...
timeout /t 30 /nobreak

railway domain
echo.

set /p url="Copiaza URL-ul de mai sus si lipeste aici: "

echo.
echo Test %url%/health ...
echo.
curl -s "%url%/health"

echo.
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                     🎉 DEPLOYMENT FINALIZAT! 🎉                       ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo Ar trebui sa vezi:
echo   {"status":"ok","database":"connected"}
echo.
echo Daca vezi asta, aplicatia merge perfect! 🎉
echo.
echo Acceseaza: %url%
echo.
echo Comenzi utile:
echo   railway logs            (vezi logs)
echo   railway open            (dashboard)
echo   railway restart         (restart)
echo.
pause

