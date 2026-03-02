"""Procesare OCR cu Tesseract (folosit din pdf_processor când PDF-ul e scan)."""
import subprocess
import sys
from pathlib import Path


def check_tesseract_installed() -> bool:
    """Verifică dacă Tesseract e instalat și în PATH."""
    try:
        subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# Utilizare: textul se extrage în pdf_processor via _run_ocr().
# Acest modul poate fi extins cu preprocesare imagine (contrast, binarizare) pentru OCR mai bun.
