@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

REM =============================================================================
REM  CREATOR PACHET DEPLOYMENT - CPANEL (ROMARG HOSTING)
REM  Pregătește aplicația pentru upload pe hosting PHP
REM =============================================================================

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║     📦 CREATOR PACHET CPANEL - ROMARG HOSTING 📦                      ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo Acest script va crea un pachet ZIP pregătit pentru:
echo   ✓ Upload pe cPanel File Manager
echo   ✓ MySQL database setup
echo   ✓ PHP 7+ compatible
echo   ✓ Instalare automată cu installer.php
echo.
pause

REM ─────────────────────────────────────────────────────────────────────────────
REM  Verificare Python
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo [1/4] Verificare Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Python nu este instalat!
    pause
    exit /b 1
)
echo ✓ Python găsit.

REM ─────────────────────────────────────────────────────────────────────────────
REM  Creare director deployment
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo [2/4] Pregătire fișiere pentru deployment...

set DEPLOY_DIR=deployment_cpanel
if exist "%DEPLOY_DIR%" (
    echo → Șterg director vechi...
    rmdir /s /q "%DEPLOY_DIR%"
)

mkdir "%DEPLOY_DIR%"
mkdir "%DEPLOY_DIR%\backend"
mkdir "%DEPLOY_DIR%\sql"
mkdir "%DEPLOY_DIR%\buletine"

echo ✓ Directoare create.

REM ─────────────────────────────────────────────────────────────────────────────
REM  Copiere fișiere
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo [3/4] Copiere fișiere...

REM Copiere backend Python
xcopy /E /I /Q backend "%DEPLOY_DIR%\backend\" >nul
xcopy /E /I /Q sql "%DEPLOY_DIR%\sql\" >nul

REM Copiere fișiere root
copy requirements.txt "%DEPLOY_DIR%\" >nul
copy run_migrations.py "%DEPLOY_DIR%\" >nul 2>nul
copy .env.example "%DEPLOY_DIR%\.env.example" >nul

echo ✓ Fișiere copiate.

REM ─────────────────────────────────────────────────────────────────────────────
REM  Creare fișiere suplimentare
REM ─────────────────────────────────────────────────────────────────────────────
echo.
echo [4/4] Generare fișiere instalare...

REM Se vor genera în următorul pas
echo ✓ Pregătit pentru generare.

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║              📦 PACHET PREGĂTIT CU SUCCES! 📦                          ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.
echo Director creat: %DEPLOY_DIR%\
echo.
echo Următorii pași:
echo   1. Voi genera fișierele PHP pentru instalare
echo   2. Voi crea arhiva ZIP
echo   3. Voi genera instrucțiunile de deployment
echo.
pause

python -c "import sys; print('Python version:', sys.version)"
echo.
echo Apasă orice tastă pentru a continua cu generarea fișierelor PHP...
pause >nul

REM Aici se va apela scriptul Python pentru generare
python generate_cpanel_installer.py

if exist "%DEPLOY_DIR%.zip" (
    echo.
    echo ✓ Arhiva ZIP creată: %DEPLOY_DIR%.zip
    echo ✓ Mărime: 
    dir "%DEPLOY_DIR%.zip" | find ".zip"
)

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo  FINALIZAT!
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo Fișiere generate:
echo   • %DEPLOY_DIR%.zip        - Pentru upload pe cPanel
echo   • INSTRUCTIUNI_CPANEL.txt  - Pași deployment
echo.
echo Citește INSTRUCTIUNI_CPANEL.txt pentru pașii următori!
echo.
pause
