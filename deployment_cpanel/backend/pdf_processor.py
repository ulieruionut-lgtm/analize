"""Detectare tip PDF (text vs scan) + extragere text.
- PDF cu text: pdfplumber
- PDF scanat: PyMuPDF (fitz) pentru imagini + Tesseract OCR
  PyMuPDF nu are nevoie de poppler - merge pe Windows fara instalare extra.
"""
from pathlib import Path
from typing import Tuple

import pdfplumber

from config import settings


def _run_ocr_pymupdf(pdf_path: str) -> Tuple[str, str | None]:
    """
    Converteste PDF la imagini cu PyMuPDF (fitz) si ruleaza Tesseract OCR.
    Nu necesita poppler - PyMuPDF este self-contained.
    """
    # 1. Verifica PyMuPDF
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return "", "PyMuPDF nu este instalat. Ruleaza: pip install pymupdf"

    # 2. Verifica Tesseract
    try:
        import pytesseract
    except ImportError:
        return "", "pytesseract nu este instalat. Ruleaza: pip install pytesseract"

    # 3. Verifica ca Tesseract e in PATH
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        return "", (
            "Tesseract nu este instalat sau nu este in PATH. "
            "Descarca de la: https://github.com/UB-Mannheim/tesseract/wiki "
            "si instaleaza cu optiunea 'Romanian' bifata. "
            "Apoi adauga C:\\Program Files\\Tesseract-OCR la variabila PATH."
        )

    # 4. Converteste PDF la imagini cu PyMuPDF si ruleaza OCR
    try:
        from PIL import Image
        import io

        doc = fitz.open(pdf_path)
        texts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Rezolutie 300 DPI pentru OCR bun
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(img, lang=settings.ocr_lang)
            texts.append(text)
        doc.close()
        return "\n".join(texts), None
    except Exception as e:
        return "", f"Eroare la OCR: {e!s}"


def extract_text_from_pdf(pdf_path: str) -> Tuple[str, str, str | None]:
    """
    Extrage text din PDF. Returneaza (text, tip, eroare_sau_None).
    - tip = 'text'  → PDF cu text direct (nu e nevoie de OCR)
    - tip = 'ocr'   → PDF scanat, s-a folosit Tesseract
    """
    # Pas 1: incearca pdfplumber (rapid, fara OCR)
    text_pdf = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_pdf += t + "\n"
    except Exception:
        pass
    text_pdf = (text_pdf or "").strip()

    # Daca textul e suficient de lung, e PDF text
    if len(text_pdf) >= settings.pdf_text_min_chars:
        return text_pdf, "text", None

    # Pas 2: PDF scanat - folosim PyMuPDF + Tesseract
    ocr_text, ocr_err = _run_ocr_pymupdf(pdf_path)
    combined = (text_pdf + "\n" + ocr_text).strip() if text_pdf else ocr_text.strip()
    return combined, "ocr", ocr_err
