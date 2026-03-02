@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

REM Adauga Git in PATH
if exist "C:\Program Files\Git\cmd\git.exe" set "PATH=%PATH%;C:\Program Files\Git\cmd"
if exist "C:\Program Files (x86)\Git\cmd\git.exe" set "PATH=%PATH%;C:\Program Files (x86)\Git\cmd"

echo.
echo ============================================================
echo   SETUP: GitHub + Deploy automat pe Railway
echo ============================================================
echo.
echo Vezi si: GHID_DEPLOY_GITHUB_RAILWAY.md
echo.
pause

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [EROARE] Git nu este instalat.
    echo Descarca: https://git-scm.com/download/win
    pause
    exit /b 1
)

if not exist ".git" (
    echo.
    echo Prima rulare - initializare Git...
    git init
    git add .
    git commit -m "Initial - Analize medicale"
    echo.
    echo [OK] Repo local creat. Acum trebuie sa conectezi la GitHub.
    echo.
    echo 1. Creeaza repo gol pe https://github.com/new
    echo 2. Introdu URL-ul mai jos (ex: https://github.com/scanaricabinet-ulieru/ionut-analize.git)
    echo.
    set /p REPO_URL="URL repo GitHub: "
    if "!REPO_URL!"=="" (
        echo Niciun URL introdus. Ruleaza scriptul din nou cand ai repo-ul.
        pause
        exit /b 0
    )
    git remote add origin "!REPO_URL!"
    git branch -M main
    echo.
    echo Push in curs (poate cere user/parola sau token)...
    git push -u origin main
    if !errorlevel! equ 0 (
        echo.
        echo [OK] Push reusit!
        echo In Railway Dashboard: Settings - Source - Connect Repo - selecteaza acest repo.
        echo Apoi Railway va face deploy automat la fiecare push.
    ) else (
        echo.
        echo Push esuat. Verifica URL-ul si credentialele GitHub.
    )
) else (
    echo.
    echo Repo exista. Commit si push...
    git add -A
    git commit -m "Update" 2>nul
    git push
    if !errorlevel! equ 0 (
        echo.
        echo [OK] Push reusit! Deploy in 1-2 minute.
    ) else (
        echo Push esuat.
    )
)

echo.
pause
