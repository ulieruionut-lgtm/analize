@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

REM Adauga Git in PATH daca nu e deja
if exist "C:\Program Files\Git\cmd\git.exe" set "PATH=%PATH%;C:\Program Files\Git\cmd"
if exist "C:\Program Files (x86)\Git\cmd\git.exe" set "PATH=%PATH%;C:\Program Files (x86)\Git\cmd"

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
    echo [EROARE] Git nu este instalat sau nu e in PATH.
    echo Inchide si redeschide CMD/ PowerShell dupa instalarea Git.
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
