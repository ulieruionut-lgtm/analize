@echo off
chcp 65001 >nul

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║        🚀 REDEPLOY RAILWAY CU SQLITE (SIMPLU!) 🚀                     ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo Aceasta varianta foloseste SQLite (fara PostgreSQL)!
echo.
echo AVANTAJ: Nu trebuie sa configurezi nimic!
echo DEZAVANTAJ: Datele se pierd la redeploy (doar pentru test/demo)
echo.
echo Pentru productie reala, recomandam PostgreSQL.
echo Dar pentru test, SQLite merge perfect!
echo.
pause

echo.
echo [1/3] Commit modificari...
echo.
git add backend/config.py railway.toml
git commit -m "Use SQLite for Railway deployment"

echo.
echo [2/3] Deploy pe Railway...
echo.
railway up

echo.
echo [3/3] Astept 30 secunde ca aplicatia sa porneasca...
echo.
timeout /t 30 /nobreak

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                     ✓ DEPLOYMENT FINALIZAT! ✓                         ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

railway domain
echo.

set /p url="Introdu URL-ul de mai sus: "

echo.
echo Test health check...
curl -s "%url%/health"

echo.
echo.
echo Ar trebui sa vezi:
echo   {"status":"ok","database":"connected"}
echo.
echo Daca merge, aplicatia este LIVE cu SQLite! 🎉
echo.
echo IMPORTANT: 
echo - Upload PDF-uri si datele se salveaza in SQLite
echo - La restart/redeploy, datele se pierd (SQLite e local)
echo - Pentru productie, trebuie PostgreSQL
echo.
pause
