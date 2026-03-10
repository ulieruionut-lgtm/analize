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


def _deskew_imagine(img):
    """Corecteaza inclinarea paginii (deskew) cu OpenCV. Returneaza PIL Image sau None daca esueaza."""
    try:
        import cv2
        import numpy as np
        from PIL import Image
        arr = np.array(img.convert("L"))
        # Detecteaza unghiul de inclinare
        coords = np.column_stack(np.where(arr < 200))
        if len(coords) < 100:
            return None
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90
        if abs(angle) < 0.5:
            return None
        (h, w) = arr.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(arr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return Image.fromarray(rotated)
    except Exception:
        return None


def _threshold_adaptiv(arr):
    """Binarizare cu threshold adaptiv (bloc) pentru contrast variabil. Returneaza numpy array."""
    try:
        import cv2
        import numpy as np
        if len(arr.shape) == 3:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        else:
            gray = arr
        # Blur usor pentru zgomot
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        return thresh
    except Exception:
        return None


def _preproceseaza_imagine_ocr(img):
    """
    Preproceseaza o imagine pentru OCR mai bun:
    1. Deskew (corectare inclinare) daca OpenCV disponibil
    2. Grayscale + contrast + sharpness
    3. Threshold adaptiv (sau fix 180 fallback)
    4. Sterge liniile subtiri de bordura
    Returneaza imaginea procesata (PIL Image).
    """
    try:
        import numpy as np
        from PIL import ImageEnhance
        from PIL import Image as PILImage

        # Deskew: corecteaza inclinarea
        deskewed = _deskew_imagine(img)
        if deskewed is not None:
            img = deskewed
        else:
            img = img.convert("L")

        # Grayscale daca nu e deja
        gray = img if img.mode == "L" else img.convert("L")

        # Mareste contrastul
        gray = ImageEnhance.Contrast(gray).enhance(2.0)
        gray = ImageEnhance.Sharpness(gray).enhance(1.5)

        # Converteste la numpy
        arr = np.array(gray)

        # Threshold adaptiv (OpenCV) pentru contrast variabil, altfel pastreaza grayscale
        thresh_arr = _threshold_adaptiv(arr)
        if thresh_arr is not None:
            arr = thresh_arr
        # Fallback: ramane grayscale (bun pentru OCR), folosim binary doar pt detectie borduri

        # Pentru detectie linii bordura: pixel negru (text/linie) = 1
        binary = (arr < 200).astype(np.uint8) if arr.max() > 1 else (arr < 200).astype(np.uint8)

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

    # TESSDATA_PREFIX pentru tessdata_best (opțional, setat în .env)
    tess_prefix = getattr(settings, "tessdata_prefix", None)
    if tess_prefix:
        import os
        os.environ["TESSDATA_PREFIX"] = str(tess_prefix)

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

        # Configuratie Tesseract din settings (PSM 3=auto table, OEM 2=LSTM+legacy)
        tess_config = f"--oem {getattr(settings, 'ocr_oem', 2)} --psm {getattr(settings, 'ocr_psm', 3)}"
        psm_fallback = getattr(settings, 'ocr_psm_fallback', 4)
        min_chars = getattr(settings, 'ocr_min_chars', 100)

        for page_num in range(len(doc)):
            page = doc[page_num]
            # 400 DPI pentru calitate mai buna
            mat = fitz.Matrix(400 / 72, 400 / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))

            # Preprocesare: deskew, contrast, threshold adaptiv, sterge borduri
            img_proc = _preproceseaza_imagine_ocr(img)

            # OCR cu configuratie din settings
            text = pytesseract.image_to_string(
                img_proc,
                lang=settings.ocr_lang,
                config=tess_config,
            )

            # Retry cu PSM fallback (ex: coloana) daca rezultatul e slab
            if len(text.strip()) < min_chars:
                fallback_config = f"--oem {getattr(settings, 'ocr_oem', 2)} --psm {psm_fallback}"
                text_fallback = pytesseract.image_to_string(
                    img.convert("L"),
                    lang=settings.ocr_lang,
                    config=fallback_config,
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
    1. PyMuPDF (fitz) - layout mai apropiat de ce asteapta parserul Bioclinica
    2. pdfplumber extract_text() + extract_tables() - fallback
    3. Tesseract OCR - pentru PDF-uri scanate
    """
    min_chars = getattr(settings, "pdf_text_min_chars", 200)

    # Pas 1: PyMuPDF (fitz) - produce layout cu o linie per element, potrivit pentru Bioclinica
    text_fitz = ""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        for page in doc:
            text_fitz += page.get_text() + "\n"
        doc.close()
        text_fitz = (text_fitz or "").strip()
    except Exception:
        pass

    # Pas 2: pdfplumber (fallback) - extract_text + tabele
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
    text_tabele = _extrage_tabele_pdfplumber(pdf_path)
    text_plumber = text_normal + ("\n" + text_tabele if text_tabele else "").strip()

    # Alege sursa: prefera fitz daca are suficiente caractere (layout mai potrivit pentru parser)
    text_combinat = text_fitz if len(text_fitz) >= min_chars else text_plumber
    if not text_combinat and text_plumber:
        text_combinat = text_plumber

    contine_numar = bool(re.search(r'\b\d+[.,]\d+\b|\b\d{2,}\b', text_combinat))
    if len(text_combinat) >= min_chars and contine_numar:
        colored = extract_colored_tokens(pdf_path)
        return text_combinat, "text", None, colored

    # Pas 3: PDF scanat - PyMuPDF + Tesseract cu preprocesare
    ocr_text, ocr_err = _run_ocr_pymupdf(pdf_path)
    combined = (text_combinat + "\n" + ocr_text).strip() if text_combinat else ocr_text.strip()
    return combined, "ocr", ocr_err, set()
