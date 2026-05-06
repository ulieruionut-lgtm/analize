@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo Export baza de date...
echo.

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe exporta_baza_date.py
) else (
    python exporta_baza_date.py
)

echo.
pause
