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


def tesseract_availability() -> Tuple[bool, str | None]:
    """
    Verifică dacă pytesseract poate apela binarul Tesseract.
    Returnează (True, None) dacă e ok, altfel (False, mesaj_utilizator).
    """
    try:
        import pytesseract
    except ImportError:
        return False, "pytesseract nu este instalat. Rulează: pip install pytesseract"

    tess_prefix = getattr(settings, "tessdata_prefix", None)
    if tess_prefix:
        import os

        os.environ["TESSDATA_PREFIX"] = str(tess_prefix)

    try:
        pytesseract.get_tesseract_version()
        return True, None
    except Exception as tess_err:
        import os
        import platform

        if platform.system() == "Windows":
            hint = (
                "Descarcă de la: https://github.com/UB-Mannheim/tesseract/wiki "
                "și instalează cu opțiunea «Romanian» bifată. "
                "Apoi adaugă C:\\Program Files\\Tesseract-OCR la PATH."
            )
        else:
            tpfx = os.environ.get("TESSDATA_PREFIX", "(negăsit)")
            hint = f"Tesseract nu e găsit în PATH. TESSDATA_PREFIX={tpfx}. Eroare: {tess_err}"
        return False, "Tesseract OCR nu este disponibil. " + hint


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


def _gray_std_mean_pil(img) -> Tuple[float, float]:
    """Deviație standard și medie pe L — contrastul scanului."""
    try:
        import numpy as np

        arr = np.array(img.convert("L"))
        return float(arr.std()), float(arr.mean())
    except Exception:
        return 50.0, 128.0


def _preproceseaza_ocr_clean(img):
    """
    Profil „scan curat”: CLAHE ușor + contrast moderat, fără binarizare adaptivă agresivă.
    """
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageEnhance

        desk = _deskew_imagine(img)
        base = desk if desk is not None else img.convert("L")
        gray = base if base.mode == "L" else base.convert("L")
        arr = np.array(gray)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        arr2 = clahe.apply(arr)
        pil = Image.fromarray(arr2)
        pil = ImageEnhance.Contrast(pil).enhance(1.4)
        pil = ImageEnhance.Sharpness(pil).enhance(1.25)
        return pil
    except Exception:
        return img.convert("L")


def _apply_ocr_preprocess_profile(img, profile: str):
    """profile: 'clean' | 'hard'"""
    if profile == "clean":
        return _preproceseaza_ocr_clean(img)
    return _preproceseaza_imagine_ocr(img)


def _pick_primary_preprocess_name(pil_img) -> str:
    if not getattr(settings, "ocr_preprocess_auto", False):
        return "hard"
    try:
        std, _mean = _gray_std_mean_pil(pil_img)
        if std < 38.0:
            return "hard"
        return "clean"
    except Exception:
        return "hard"


def _tesseract_word_metrics(image, lang: str, config: str, pytesseract_mod):
    """(mean_conf, weak_ratio, digit_ratio, n_words) pe nivel cuvânt."""
    from pytesseract import Output

    weak_thr = int(getattr(settings, "ocr_weak_word_conf", 60))
    try:
        d = pytesseract_mod.image_to_data(
            image, lang=lang, config=config, output_type=Output.DICT
        )
    except Exception:
        return 0.0, 1.0, 0.0, 0

    n = len(d.get("text", []))
    if n == 0:
        return 0.0, 1.0, 0.0, 0

    confs: list[int] = []
    weak = 0
    chars_digit = 0
    chars_alpha = 0
    n_words = 0
    levels = d.get("level", [0] * n)
    texts = d.get("text", [])
    confs_raw = d.get("conf", [])

    for i in range(n):
        try:
            if int(levels[i]) != 5:
                continue
        except (ValueError, TypeError, KeyError, IndexError):
            continue
        word = (texts[i] or "").strip()
        if not word:
            continue
        try:
            c = int(float(confs_raw[i]))
        except (ValueError, TypeError, KeyError, IndexError):
            continue
        if c < 0:
            continue
        n_words += 1
        confs.append(c)
        if c < weak_thr:
            weak += 1
        for ch in word:
            if ch.isdigit():
                chars_digit += 1
            elif ch.isalpha():
                chars_alpha += 1

    mean_c = sum(confs) / len(confs) if confs else 0.0
    weak_ratio = weak / n_words if n_words else 1.0
    tot = chars_digit + chars_alpha
    digit_ratio = (chars_digit / tot) if tot > 0 else 0.0
    return mean_c, weak_ratio, digit_ratio, n_words


def _ocr_quality_score(
    text: str,
    mean_c: float,
    weak_ratio: float,
    digit_ratio: float,
    n_words: int,
    min_chars: int,
) -> float:
    t = (text or "").strip()
    L = len(t)
    if L == 0 and n_words == 0:
        return -1e9
    score = mean_c * 0.45
    score += min(L / 8.0, 45.0)
    score -= weak_ratio * 38.0
    score += digit_ratio * 22.0
    if L < min_chars:
        score -= (min_chars - L) * 0.55
    if n_words == 0 and L > 5:
        score -= 15.0
    return score


def _ocr_needs_more_passes(
    text: str,
    mean_c: float,
    weak_ratio: float,
    digit_ratio: float,
    n_words: int,
    min_chars: int,
) -> bool:
    t = (text or "").strip()
    if len(t) < min_chars:
        return True
    if not getattr(settings, "ocr_use_metrics_retry", True):
        return False
    if n_words == 0:
        return len(t) < max(min_chars, 80)
    if mean_c < float(getattr(settings, "ocr_retry_min_mean_conf", 48.0)):
        return True
    if weak_ratio > float(getattr(settings, "ocr_retry_max_weak_ratio", 0.45)):
        return True
    mdr = float(getattr(settings, "ocr_min_digit_ratio", 0.0) or 0.0)
    if mdr > 0 and len(t) >= min_chars and digit_ratio < mdr:
        return True
    return False


def _tesseract_cfg(oem: int, psm: int, dpi: int) -> str:
    return f"--oem {oem} --psm {psm} -c user_defined_dpi={dpi}"


def _infer_psm_from_vertical_layout(gray_arr) -> int | None:
    """Sugerează PSM 4 dacă există faleză verticală centrală (2 coloane)."""
    try:
        import cv2
        import numpy as np

        h, w = gray_arr.shape
        if w < 500 or h < 400:
            return None
        _, bw = cv2.threshold(gray_arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        ink = (bw < 200).astype(np.uint8)
        proj = ink.sum(axis=0).astype(np.float64)
        mx = proj.max()
        if mx <= 0:
            return None
        projn = proj / mx
        sm = np.convolve(projn, np.ones(15) / 15.0, mode="same")
        low = sm < 0.11
        best_w = 0
        best_mid = None
        i = 0
        while i < w:
            if not low[i]:
                i += 1
                continue
            j = i
            while j < w and low[j]:
                j += 1
            gap = j - i
            mid = (i + j) // 2
            if gap >= max(12, w // 55) and 0.24 * w < mid < 0.76 * w and gap > best_w:
                best_w = gap
                best_mid = mid
            i = j
        if best_mid is None or best_w < max(12, w // 55):
            return None
        return 4
    except Exception:
        return None


def _split_page_into_column_images(pil_img):
    import numpy as np
    import cv2

    im = pil_img if pil_img.mode == "RGB" else pil_img.convert("RGB")
    arr = np.array(im.convert("L"))
    h, w = arr.shape
    if w < 400:
        return None
    try:
        _, bw = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        ink = (bw < 200).astype(np.uint8)
        proj = ink.sum(axis=0).astype(np.float64)
        mx = proj.max()
        if mx < h * 0.04:
            return None
        projn = proj / (mx + 1e-6)
        sm = np.convolve(projn, np.ones(15) / 15.0, mode="same")
        low = sm < 0.12
        best_w = 0
        best_x = None
        i = 0
        while i < w:
            if not low[i]:
                i += 1
                continue
            j = i
            while j < w and low[j]:
                j += 1
            gap = j - i
            mid = (i + j) // 2
            if gap >= max(12, w // 60) and 0.22 * w < mid < 0.78 * w and gap > best_w:
                best_w = gap
                best_x = int(mid)
            i = j
        if best_x is None:
            return None
        lw, rw = best_x, w - best_x
        if lw < int(0.27 * w) or rw < int(0.27 * w):
            return None
        return [im.crop((0, 0, best_x, h)), im.crop((best_x, 0, w, h))]
    except Exception:
        return None


def _try_ocr_split_columns(
    pil_rgb, lang: str, base_cfg: str, pytesseract_mod, min_chars: int
) -> str | None:
    cols = _split_page_into_column_images(pil_rgb)
    if not cols or len(cols) < 2:
        return None
    parts = []
    for c in cols:
        try:
            t = pytesseract_mod.image_to_string(c, lang=lang, config=base_cfg).strip()
        except Exception:
            t = ""
        parts.append(t)
    merged = "\n".join(p for p in parts if p)
    if len(merged.strip()) < max(20, min_chars // 2):
        return None
    return merged


def _ocr_pass_string_and_metrics(
    pil_img, lang: str, tess_cfg: str, pytesseract_mod
) -> Tuple[str, float, float, float, int]:
    text = pytesseract_mod.image_to_string(pil_img, lang=lang, config=tess_cfg) or ""
    mean_c, weak_r, dig_r, n_w = _tesseract_word_metrics(
        pil_img, lang, tess_cfg, pytesseract_mod
    )
    return text, mean_c, weak_r, dig_r, n_w


def _ocr_best_for_page_rgb(
    img_rgb, pytesseract_mod, min_chars: int, dpi_hint: int, oem: int
) -> str:
    lang = settings.ocr_lang
    psm_user = int(getattr(settings, "ocr_psm", 3))
    psm_fb = int(getattr(settings, "ocr_psm_fallback", 4))
    psm_sp = int(getattr(settings, "ocr_psm_sparse", 11))

    if getattr(settings, "ocr_column_segmentation", False):
        cfg_try = _tesseract_cfg(oem, psm_user, dpi_hint)
        col_merged = _try_ocr_split_columns(
            img_rgb, lang, cfg_try, pytesseract_mod, min_chars
        )
        if col_merged:
            cm = col_merged.strip()
            if len(cm) >= min_chars or (len(cm) >= 40 and re.search(r"\d", cm)):
                return col_merged

    psm_main = psm_user
    if getattr(settings, "ocr_layout_auto", False):
        try:
            import numpy as np

            arr = np.array(img_rgb.convert("L"))
            guess = _infer_psm_from_vertical_layout(arr)
            if guess is not None:
                psm_main = guess
        except Exception:
            pass

    primary = _pick_primary_preprocess_name(img_rgb)
    secondary = "hard" if primary == "clean" else "clean"

    def pass_(img_prep, psm: int):
        cfg = _tesseract_cfg(oem, psm, dpi_hint)
        return _ocr_pass_string_and_metrics(img_prep, lang, cfg, pytesseract_mod)

    img_a = _apply_ocr_preprocess_profile(img_rgb, primary)
    text, mean_c, weak_r, dig_r, n_w = pass_(img_a, psm_main)
    best_t = text
    best_sc = _ocr_quality_score(text, mean_c, weak_r, dig_r, n_w, min_chars)
    img_best = img_a
    best_mean, best_weak, best_dig, best_nw = mean_c, weak_r, dig_r, n_w

    if (
        _ocr_needs_more_passes(text, mean_c, weak_r, dig_r, n_w, min_chars)
        and secondary != primary
    ):
        img_b = _apply_ocr_preprocess_profile(img_rgb, secondary)
        t2, m2, w2, d2, n2 = pass_(img_b, psm_main)
        s2 = _ocr_quality_score(t2, m2, w2, d2, n2, min_chars)
        if s2 > best_sc:
            best_t, best_sc = t2, s2
            img_best = img_b
            best_mean, best_weak, best_dig, best_nw = m2, w2, d2, n2

    if _ocr_needs_more_passes(
        best_t, best_mean, best_weak, best_dig, best_nw, min_chars
    ):
        for psm_x in (psm_fb, psm_sp):
            if psm_x == psm_main:
                continue
            t3, m3, w3, d3, n3 = pass_(img_best, psm_x)
            s3 = _ocr_quality_score(t3, m3, w3, d3, n3, min_chars)
            if s3 > best_sc:
                best_t, best_sc = t3, s3
                best_mean, best_weak, best_dig, best_nw = m3, w3, d3, n3

    if _ocr_needs_more_passes(
        best_t, best_mean, best_weak, best_dig, best_nw, min_chars
    ):
        gimg = img_rgb.convert("L")
        for psm_x in (psm_fb, psm_sp):
            t4, m4, w4, d4, n4 = pass_(gimg, psm_x)
            s4 = _ocr_quality_score(t4, m4, w4, d4, n4, min_chars)
            if s4 > best_sc:
                best_t, best_sc = t4, s4

    return best_t


def _preproceseaza_imagine_ocr(img):
    """
    Profil „dificil” pentru OCR:
    1. Deskew (corectare inclinare) daca OpenCV disponibil
    2. Grayscale + contrast + sharpness
    3. Threshold adaptiv
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
        return "", "pytesseract nu este instalat. Rulează: pip install pytesseract"

    ok, err = tesseract_availability()
    if not ok:
        return "", err or "Tesseract OCR nu este disponibil."

    try:
        from PIL import Image
        import io

        doc = fitz.open(pdf_path)
        texts = []

        oem = getattr(settings, "ocr_oem", 2)
        min_chars = getattr(settings, "ocr_min_chars", 100)
        dpi_hint = getattr(settings, "ocr_dpi_hint", 400)

        for page_num in range(len(doc)):
            page = doc[page_num]
            mat = fitz.Matrix(dpi_hint / 72, dpi_hint / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            if img.mode != "RGB":
                img = img.convert("RGB")

            text = _ocr_best_for_page_rgb(
                img, pytesseract, min_chars, dpi_hint, oem
            )
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


def extract_text_from_pdf(pdf_path: str) -> Tuple[str, str, str | None, set, str]:
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

    # Pas 1: PyMuPDF - produce layout cu o linie per element, potrivit pentru Bioclinica
    # Folosim "import pymupdf" explicit pentru a evita conflictul cu pachetul vechi "fitz" de pe PyPI
    text_fitz = ""
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        for page in doc:
            # sort=True: ordine de citire (stânga→dreapta, sus→jos) — important pentru tabele
            # Affidea/Hiperdia și alte buletine multi-pagină; altfel textul din coloane se amestecă.
            try:
                text_fitz += page.get_text(sort=True) + "\n"
            except TypeError:
                text_fitz += page.get_text() + "\n"
        doc.close()
        text_fitz = (text_fitz or "").strip()
    except Exception:
        try:
            import fitz  # fallback: pymupdf se exporta si ca fitz
            doc = fitz.open(pdf_path)
            for page in doc:
                try:
                    text_fitz += page.get_text(sort=True) + "\n"
                except TypeError:
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

    # COMBINĂ textul din ambele surse pentru a maximiza analizele extrase.
    # pdfplumber și pymupdf au layout-uri diferite - unele analize apar doar într-o sursă
    # (ex: TGO valoare pe pg.2 după header - una o extrage, cealaltă nu).
    # Parserul are deduplicare, deci nu vom avea duplicate.
    extractor_used = "pymupdf"
    text_combinat = (text_fitz or "").strip()
    text_plumber_clean = (text_plumber or "").strip()
    if text_plumber_clean:
        if text_combinat:
            text_combinat = text_combinat + "\n" + text_plumber_clean
            extractor_used = "pymupdf+pdfplumber"
        else:
            text_combinat = text_plumber_clean
            extractor_used = "pdfplumber"

    contine_numar = bool(re.search(r'\b\d+[.,]\d+\b|\b\d{2,}\b', text_combinat))
    # Text suficient dar fără zecimale evidente (ex. doar „Negativ”, CNP) — tot merită parsat
    if len(text_combinat) >= min_chars and contine_numar:
        colored = extract_colored_tokens(pdf_path)
        return text_combinat, "text", None, colored, extractor_used
    if len(text_combinat) >= min_chars * 2:
        colored = extract_colored_tokens(pdf_path)
        return text_combinat, "text", None, colored, extractor_used

    # Pas 3: PDF scanat - PyMuPDF + Tesseract cu preprocesare
    ocr_text, ocr_err = _run_ocr_pymupdf(pdf_path)
    combined = (text_combinat + "\n" + ocr_text).strip() if text_combinat else ocr_text.strip()
    ocr_extractor = f"{extractor_used}+ocr" if text_combinat.strip() else "ocr"
    return combined, "ocr", ocr_err, set(), ocr_extractor
