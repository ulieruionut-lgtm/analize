@echo off
chcp 65001 >nul
cd /d "D:\Ionut analize"

echo.
echo === DEPLOY FINAL ===
echo.

railway up

echo.
echo Astept 2 minute...
timeout /t 120 /nobreak >nul

echo.
echo TEST...
powershell -NoProfile -Command "try { $r = Invoke-RestMethod -Uri 'https://ionut-analize-app-production.up.railway.app/health' -TimeoutSec 20; Write-Host 'SUCCESS!' -ForegroundColor Green; $r | ConvertTo-Json } catch { Write-Host 'Error:' $_.Exception.Message -ForegroundColor Red; railway logs 2>&1 | Select-Object -Last 20 }"

echo.
echo URL: https://ionut-analize-app-production.up.railway.app
echo.
pause
