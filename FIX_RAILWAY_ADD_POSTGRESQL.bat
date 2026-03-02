@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║        🔧 FIX RAILWAY - ADAUGĂ POSTGRESQL 🔧                          ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo Aplicația rulează, dar lipsește database-ul PostgreSQL!
echo.
echo PAȘI DE URMAT:
echo.
echo 1. Deschide Railway Dashboard
echo.
pause
echo.
echo → Deschid Railway dashboard...
railway open
echo.
echo 2. În Railway Dashboard:
echo.
echo    a) Click pe PROIECTUL tău (analize-medicale)
echo    b) Click pe butonul "+ New" (sus-dreapta)
echo    c) Selectează "Database"
echo    d) Selectează "PostgreSQL"
echo    e) Click "Add PostgreSQL"
echo.
echo    Railway va crea database-ul AUTOMAT (30 secunde)
echo    DATABASE_URL se va configura AUTOMAT!
echo.
pause
echo.
echo 3. Așteaptă 30 secunde ca PostgreSQL să pornească...
echo.
timeout /t 30 /nobreak
echo.
echo 4. Rulează migrațiile (creează tabelele)
echo.
railway run python run_migrations.py
if %errorlevel% neq 0 (
    echo.
    echo ⚠ Migrațiile au eșuat! Probabil PostgreSQL nu e gata încă.
    echo.
    echo Așteaptă 1 minut și încearcă manual:
    echo   railway run python run_migrations.py
    echo.
    pause
    exit /b 1
)
echo.
echo ✓ Migrații executate cu succes!
echo.
echo 5. Restart aplicație pentru a reciti DATABASE_URL
echo.
railway up --detach
echo.
echo ✓ Aplicația se repornește...
echo.
timeout /t 10 /nobreak
echo.
echo 6. TEST FINAL
echo.
set /p app_url="Introdu URL-ul aplicației (ex: https://analize-xxx.railway.app): "
echo.
echo → Test health check: %app_url%/health
echo.
curl -s "%app_url%/health"
echo.
echo.
echo Ar trebui să vezi:
echo   {"status":"ok","database":"connected"}
echo.
echo Dacă vezi "connected" → SUCCESS! 🎉
echo Dacă vezi doar "OK" → PostgreSQL încă nu e gata, mai așteaptă 1 min
echo.
pause
echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║                     🎉 FINALIZAT! 🎉                                   ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo Dacă tot nu merge, rulează:
echo   railway logs --follow
echo.
echo și vezi ce erori apar.
echo.
pause
