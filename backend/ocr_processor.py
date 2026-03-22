"""Integrare Tesseract: verificare disponibilitate partajată cu pdf_processor.

Preprocesare și OCR propriu-zis: backend.pdf_processor (_run_ocr_pymupdf).
"""
from __future__ import annotations

from typing import Tuple

from backend.pdf_processor import tesseract_availability


def check_tesseract_installed() -> bool:
    """Returnează True dacă Tesseract răspunde (pytesseract)."""
    ok, _ = tesseract_availability()
    return ok


def tesseract_status() -> Tuple[bool, str | None]:
    """(disponibil, mesaj_eroare_sau_None) — util pentru health checks."""
    return tesseract_availability()
