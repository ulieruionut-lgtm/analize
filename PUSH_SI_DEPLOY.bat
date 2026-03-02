@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================
echo   PUSH + Deploy automat
echo ============================================
echo.
echo Daca Railway e conectat la GitHub,
echo push-ul declansa deploy automat.
echo.

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [EROARE] Git nu este instalat.
    pause
    exit /b 1
)

if not exist ".git" (
    echo Nu exista repo Git. Ruleaza CONECTARE_GITHUB_SI_DEPLOY.bat prima data.
    pause
    exit /b 1
)

git add -A
git status
git commit -m "Update" 2>nul
git push

if %errorlevel% equ 0 (
    echo.
    echo [OK] Push reusit! Asteapta 1-2 minute pentru deploy.
    echo URL: https://ionut-analize-app-production.up.railway.app
) else (
    echo.
    echo Push esuat. Verifica conectivitatea si credentialele.
)

echo.
pause
