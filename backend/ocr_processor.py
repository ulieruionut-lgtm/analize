"""Procesare OCR cu Tesseract (folosit din pdf_processor când PDF-ul e scan).

Îmbunătățiri: preprocesare imagine în pdf_processor (deskew, contrast, PSM + fallback + sparse),
limba ron+eng din setări. Tesseract **nu** învață din PDF-urile tale: e model static.
„Învățare permanentă” în app = reguli în parser + aliasuri în DB / corecții manuale la pacient.
Pentru AI vizual antrenabil ar fi nevoie de alt serviciu (ex. cloud Vision cu fine-tuning).
"""
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
