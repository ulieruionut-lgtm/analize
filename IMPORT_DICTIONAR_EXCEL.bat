@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo Import dictionar analize din Excel...
echo (dictionar_analize_300_1200_alias.xlsx)
echo.

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe import_dictionar_excel.py
) else (
    python import_dictionar_excel.py
)

echo.
pause
