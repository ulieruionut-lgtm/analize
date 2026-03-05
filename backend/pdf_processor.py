"""Detectare tip PDF (text vs scan) + extragere text.
- PDF cu text: pdfplumber (extract_text + extract_tables pentru tabele cu borduri)
- PDF scanat: PyMuPDF (fitz) pentru imagini + preprocesare + Tesseract OCR
  PyMuPDF nu are nevoie de poppler - merge pe Windows fara instalare extra.
"""
import re
from pathlib import Path
from typing import Tuple

import pdfplumber

from backend.config import settings


def _extrage_tabele_pdfplumber(pdf_path: str) -> str:
    """
    Extrage continut din tabele cu borduri folosind pdfplumber extract_tables().
    Returneaza text formatat ca linii 'parametru valoare unitate interval'.
    Util pentru PDF-uri Bioclinica/MedLife cu celule bordate.
    """
    linii = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tabele = page.extract_tables()
                for tabel in tabele:
                    for rand in tabel:
                        if not rand:
                            continue
                        # Curata celulele None/goale
                        celule = [str(c).strip() if c else "" for c in rand]
                        # Filtreaza randuri complet goale
                        if not any(celule):
                            continue
                        # Uneste celulele cu spatiu (parser-ul va detecta formatul)
                        linie = "  ".join(c for c in celule if c)
                        if linie:
                            linii.append(linie)
    except Exception:
        pass
    return "\n".join(linii)


def _preproceseaza_imagine_ocr(img):
    """
    Preproceseaza o imagine pentru OCR mai bun:
    1. Converteste la grayscale
    2. Mareste contrastul
    3. Sterge liniile subtiri de bordura (detectie numpy)
    4. Binarizeaza
    Returneaza imaginea procesata (PIL Image).
    """
    try:
        import numpy as np
        from PIL import ImageEnhance, ImageFilter

        # Grayscale
        gray = img.convert("L")

        # Mareste contrastul
        gray = ImageEnhance.Contrast(gray).enhance(2.0)
        gray = ImageEnhance.Sharpness(gray).enhance(1.5)

        # Converteste la numpy pentru procesare linii
        arr = np.array(gray)

        # Binarizare: pixeli inchisi (< 180) -> negru, restul -> alb
        binary = (arr < 180).astype(np.uint8)

        # Sterge liniile orizontale de bordura:
        # O linie e "bordura" daca > 90% din pixeli sunt negri
        # SI este subtire (1-3 pixeli consecutivi) - evita stergerea textului dens
        i = 0
        while i < binary.shape[0]:
            if binary[i].mean() > 0.90:
                # Detectam cat de groasa e linia (linii consecutive)
                j = i + 1
                while j < binary.shape[0] and binary[j].mean() > 0.90:
                    j += 1
                grosime = j - i
                if grosime <= 4:  # bordura subtire (1-4px) - sterge
                    arr[i:j] = 255
                i = j
            else:
                i += 1

        # Sterge liniile verticale de bordura (la fel, max 4px grosime)
        j = 0
        while j < binary.shape[1]:
            if binary[:, j].mean() > 0.90:
                k = j + 1
                while k < binary.shape[1] and binary[:, k].mean() > 0.90:
                    k += 1
                grosime = k - j
                if grosime <= 4:
                    arr[:, j:k] = 255
                j = k
            else:
                j += 1

        from PIL import Image as PILImage
        return PILImage.fromarray(arr)
    except Exception:
        # Daca preprocesarea esueaza, returneaza imaginea originala
        return img.convert("L")


def _run_ocr_pymupdf(pdf_path: str) -> Tuple[str, str | None]:
    """
    Converteste PDF la imagini cu PyMuPDF (fitz) si ruleaza Tesseract OCR.
    Aplica preprocesare imagine pentru rezultate mai bune pe tabele cu borduri.
    """
    try:
        import fitz
    except ImportError:
        return "", "PyMuPDF nu este instalat. Ruleaza: pip install pymupdf"

    try:
        import pytesseract
    except ImportError:
        return "", "pytesseract nu este instalat. Ruleaza: pip install pytesseract"

    try:
        pytesseract.get_tesseract_version()
    except Exception as tess_err:
        import os, platform
        if platform.system() == "Windows":
            hint = ("Descarca de la: https://github.com/UB-Mannheim/tesseract/wiki "
                    "si instaleaza cu optiunea 'Romanian' bifata. "
                    "Apoi adauga C:\\Program Files\\Tesseract-OCR la variabila PATH.")
        else:
            tpfx = os.environ.get("TESSDATA_PREFIX", "(negasit)")
            hint = f"Tesseract nu e gasit in PATH. TESSDATA_PREFIX={tpfx}. Eroare: {tess_err}"
        return "", "Tesseract OCR nu este disponibil. " + hint

    try:
        from PIL import Image
        import io

        doc = fitz.open(pdf_path)
        texts = []

        # Configuratie Tesseract: LSTM engine + bloc uniform de text
        tess_config = "--oem 1 --psm 6"

        for page_num in range(len(doc)):
            page = doc[page_num]
            # 400 DPI pentru calitate mai buna (anterior: 300)
            mat = fitz.Matrix(400 / 72, 400 / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))

            # Preprocesare: sterge borduri, mareste contrast
            img_proc = _preproceseaza_imagine_ocr(img)

            # OCR cu configuratie imbunatatita
            text = pytesseract.image_to_string(
                img_proc,
                lang=settings.ocr_lang,
                config=tess_config,
            )

            # Daca rezultatul e slab, incearca si cu imaginea originala (PSM 4)
            if len(text.strip()) < 100:
                text_fallback = pytesseract.image_to_string(
                    img.convert("L"),
                    lang=settings.ocr_lang,
                    config="--oem 1 --psm 4",
                )
                if len(text_fallback.strip()) > len(text.strip()):
                    text = text_fallback

            texts.append(text)
        doc.close()
        return "\n".join(texts), None
    except Exception as e:
        return "", f"Eroare la OCR: {e!s}"


def extract_colored_tokens(pdf_path: str) -> set:
    """
    Extrage valorile numerice scrise cu culoare non-neagra din PDF text.
    Returneaza un set de stringuri (ex: {'12.5', '0.8'}).
    Folosit pentru detectie automata valori anormale colorate de laborator.
    Functioneaza doar pentru PDF-uri text (nu scanate).
    """
    import re as _re
    colored = set()
    try:
        import fitz
        doc = fitz.open(pdf_path)
        for page in doc:
            blocks = page.get_text("dict").get("blocks", [])
            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        color = span.get("color", 0)
                        if color != 0:  # non-negru (negrul pur = 0 in pymupdf)
                            nums = _re.findall(r'\d+[.,]\d+|\d+', span.get("text", ""))
                            colored.update(nums)
        doc.close()
    except Exception:
        pass
    return colored


def extract_text_from_pdf(pdf_path: str) -> Tuple[str, str, str | None, set]:
    """
    Extrage text din PDF. Returneaza (text, tip, eroare_sau_None, colored_tokens).
    - tip = 'text'  → PDF cu text direct (nu e nevoie de OCR)
    - tip = 'ocr'   → PDF scanat, s-a folosit Tesseract
    - colored_tokens = set de valori numerice scrise cu culoare non-neagra (doar pt text PDFs)

    Strategii de extragere (in ordine):
    1. pdfplumber extract_text() - text normal
    2. pdfplumber extract_tables() - tabele cu borduri (prinde valori in celule)
    3. Tesseract OCR cu preprocesare - pentru PDF-uri scanate
    """
    # Pas 1: incearca pdfplumber extract_text() (rapid, fara OCR)
    text_normal = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_normal += t + "\n"
    except Exception:
        pass
    text_normal = (text_normal or "").strip()

    # Pas 2: extrage si continut din tabele cu borduri (prinde valorile in celule)
    text_tabele = _extrage_tabele_pdfplumber(pdf_path)

    # Combina text normal + tabele (tabele pot contine valori ratate de extract_text)
    text_combinat = text_normal
    if text_tabele:
        text_combinat = text_normal + "\n" + text_tabele if text_normal else text_tabele
    text_combinat = text_combinat.strip()

    # Daca textul combinat e suficient de lung SI contine cel putin un numar
    # (valoare potentiala de analiza), e PDF text
    contine_numar = bool(re.search(r'\b\d+[.,]\d+\b|\b\d{2,}\b', text_combinat))
    if len(text_combinat) >= settings.pdf_text_min_chars and contine_numar:
        colored = extract_colored_tokens(pdf_path)
        return text_combinat, "text", None, colored

    # Pas 3: PDF scanat - PyMuPDF + Tesseract cu preprocesare
    ocr_text, ocr_err = _run_ocr_pymupdf(pdf_path)
    combined = (text_combinat + "\n" + ocr_text).strip() if text_combinat else ocr_text.strip()
    return combined, "ocr", ocr_err, set()
