"""Detectare tip PDF (text vs scan) + extragere text.
- PDF cu text: PyMuPDF + pdfplumber
- PDF scanat: PyMuPDF → imagine → preprocesare → Tesseract OCR

Principii de performanta:
- O singura trecere per pagina (render + tsv + string dintr-un apel image_to_data)
- O singura preprocesare per pagina (fara multi-pass daca prima e suficient de buna)
- Deskew cu proiectie Hough (nu minAreaRect pe 1M puncte)
- Eliminare borduri cu morfologie OpenCV (nu loop Python)
- OEM 3 (LSTM pur) implicit — mai rapid si mai precis pe text romanesc
- Groupare randuri TSV cu sweep liniar O(n log n) in loc de O(n^2)
"""
import re
from pathlib import Path
from typing import Tuple

from backend.config import settings


# ---------------------------------------------------------------------------
# Verificare disponibilitate Tesseract
# ---------------------------------------------------------------------------

def tesseract_availability() -> Tuple[bool, str | None]:
    try:
        import pytesseract
    except ImportError:
        return False, "pytesseract nu este instalat. Ruleaza: pip install pytesseract"

    tess_prefix = getattr(settings, "tessdata_prefix", None)
    if tess_prefix:
        import os
        os.environ["TESSDATA_PREFIX"] = str(tess_prefix)

    try:
        pytesseract.get_tesseract_version()
        return True, None
    except Exception as tess_err:
        import os, platform
        if platform.system() == "Windows":
            hint = (
                "Descarca de la: https://github.com/UB-Mannheim/tesseract/wiki "
                "si instaleaza cu optiunea Romanian bifata. "
                "Apoi adauga C:\\Program Files\\Tesseract-OCR la PATH."
            )
        else:
            tpfx = os.environ.get("TESSDATA_PREFIX", "(negasit)")
            hint = f"Tesseract nu e gasit in PATH. TESSDATA_PREFIX={tpfx}. Eroare: {tess_err}"
        return False, "Tesseract OCR nu este disponibil. " + hint


# ---------------------------------------------------------------------------
# Preprocesare imagine
# ---------------------------------------------------------------------------

def _deskew_hough(gray_arr):
    """
    Corecteaza inclinarea cu proiectie Hough (mai robusta decat minAreaRect).
    Returneaza numpy array corectat sau None daca inclinarea e neglijabila / OpenCV lipseste.
    """
    try:
        import cv2
        import numpy as np

        h, w = gray_arr.shape
        if h < 100 or w < 100:
            return None

        _, bw = cv2.threshold(gray_arr, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        # Dilata usor pentru a conecta caractere in cuvinte
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 1))
        dilated = cv2.dilate(bw, kernel, iterations=1)
        lines = cv2.HoughLinesP(dilated, 1, np.pi / 180, threshold=80,
                                minLineLength=w // 6, maxLineGap=20)
        if lines is None or len(lines) == 0:
            return None

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:
                continue
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if -15 < angle < 15:
                angles.append(angle)

        if not angles:
            return None

        # Mediana unghiurilor — rezistenta la outlieri
        angle = float(np.median(angles))
        if abs(angle) < 0.3:
            return None

        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(gray_arr, M, (w, h),
                                 flags=cv2.INTER_CUBIC,
                                 borderMode=cv2.BORDER_REPLICATE)
        return rotated
    except Exception:
        return None


def _sterge_borduri_cv(arr):
    """
    Elimina linii de bordura de tabel cu morfologie OpenCV (mult mai rapida decat loop Python).
    Returneaza array modificat sau None daca OpenCV lipseste.
    """
    try:
        import cv2
        import numpy as np

        # Lucreaza pe binar (negru = 0 = fundal, alb = 255 = text in imagine dupa threshold)
        # Linii orizontale lungi = borduri tabel
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, arr.shape[1] // 15), 1))
        h_lines = cv2.morphologyEx((255 - arr), cv2.MORPH_OPEN, h_kernel)

        # Linii verticale lungi = borduri tabel
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(40, arr.shape[0] // 15)))
        v_lines = cv2.morphologyEx((255 - arr), cv2.MORPH_OPEN, v_kernel)

        mask = cv2.add(h_lines, v_lines)
        # Unde masca e activata (borduri), punem 255 (alb = fundal)
        result = arr.copy()
        result[mask > 0] = 255
        return result
    except Exception:
        return None


def _preproceseaza_clean(img):
    """
    Profil pentru scanuri cu contrast bun: CLAHE usor + contrast moderat + deskew.
    NU aplica threshold adaptiv agresiv care mananca diacritice si caractere fine.
    """
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageEnhance

        gray_arr = np.array(img.convert("L"))

        # Deskew cu Hough
        deskewed = _deskew_hough(gray_arr)
        if deskewed is not None:
            gray_arr = deskewed

        # CLAHE pentru uniformizare iluminare
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray_arr = clahe.apply(gray_arr)

        pil = Image.fromarray(gray_arr)
        pil = ImageEnhance.Contrast(pil).enhance(1.4)
        pil = ImageEnhance.Sharpness(pil).enhance(1.2)
        return pil
    except Exception:
        return img.convert("L")


def _preproceseaza_hard(img):
    """
    Profil pentru scanuri cu contrast slab / fond gri: threshold adaptiv + stergere borduri.
    """
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageEnhance

        gray_arr = np.array(img.convert("L"))

        # Deskew cu Hough
        deskewed = _deskew_hough(gray_arr)
        if deskewed is not None:
            gray_arr = deskewed

        # Contrast + sharpness inainte de threshold
        pil = Image.fromarray(gray_arr)
        pil = ImageEnhance.Contrast(pil).enhance(1.8)
        pil = ImageEnhance.Sharpness(pil).enhance(1.4)
        gray_arr = np.array(pil)

        # Threshold adaptiv gaussian
        blurred = cv2.GaussianBlur(gray_arr, (3, 3), 0)
        thresh = cv2.adaptiveThreshold(blurred, 255,
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 15, 4)

        # Sterge borduri de tabel cu morfologie
        cleaned = _sterge_borduri_cv(thresh)
        if cleaned is not None:
            thresh = cleaned

        return Image.fromarray(thresh)
    except Exception:
        return img.convert("L")


def _pick_profile(pil_img) -> str:
    """Alege profilul de preprocesare pe baza contrastului imaginii."""
    if not getattr(settings, "ocr_preprocess_auto", True):
        return "hard"
    try:
        import numpy as np
        arr = np.array(pil_img.convert("L"))
        std = float(arr.std())
        return "clean" if std >= 38.0 else "hard"
    except Exception:
        return "hard"


def _apply_profile(img, profile: str):
    if profile == "clean":
        return _preproceseaza_clean(img)
    return _preproceseaza_hard(img)


# ---------------------------------------------------------------------------
# Nucleul OCR: un singur apel image_to_data per incercare
# (extragem atat textul cat si metricile de calitate dintr-un singur apel)
# ---------------------------------------------------------------------------

def _ocr_page_once(pil_img, lang: str, cfg: str, pytesseract_mod) -> Tuple[str, float, float, int]:
    """
    Ruleaza un singur image_to_data si returneaza (text, mean_conf, weak_ratio, n_words).
    Evita apelul dublu image_to_string + image_to_data din versiunea anterioara.
    """
    from pytesseract import Output
    weak_thr = int(getattr(settings, "ocr_weak_word_conf", 55))
    try:
        d = pytesseract_mod.image_to_data(pil_img, lang=lang, config=cfg,
                                          output_type=Output.DICT)
    except Exception:
        return "", 0.0, 1.0, 0

    n = len(d.get("text", []))
    if n == 0:
        return "", 0.0, 1.0, 0

    words_text = []
    confs = []
    weak = 0
    levels = d.get("level", [])
    texts = d.get("text", [])
    confs_raw = d.get("conf", [])

    for i in range(n):
        try:
            if int(levels[i]) != 5:
                continue
        except (ValueError, TypeError):
            continue
        word = (texts[i] or "").strip()
        if not word:
            continue
        try:
            c = int(float(confs_raw[i]))
        except (ValueError, TypeError):
            continue
        if c < 0:
            continue
        words_text.append(word)
        confs.append(c)
        if c < weak_thr:
            weak += 1

    text = " ".join(words_text)
    n_w = len(confs)
    mean_c = sum(confs) / n_w if n_w else 0.0
    weak_r = weak / n_w if n_w else 1.0
    return text, mean_c, weak_r, n_w


def _ocr_quality_score(text: str, mean_c: float, weak_r: float, n_words: int, min_chars: int) -> float:
    L = len((text or "").strip())
    if L == 0 and n_words == 0:
        return -1e9
    score = mean_c * 0.45
    score += min(L / 8.0, 45.0)
    score -= weak_r * 38.0
    if L < min_chars:
        score -= (min_chars - L) * 0.55
    if n_words == 0 and L > 5:
        score -= 15.0
    return score


def _needs_retry(text: str, mean_c: float, weak_r: float, n_words: int, min_chars: int) -> bool:
    t = (text or "").strip()
    if len(t) < min_chars:
        return True
    if not getattr(settings, "ocr_use_metrics_retry", True):
        return False
    if n_words == 0:
        return len(t) < max(min_chars, 80)
    if mean_c < float(getattr(settings, "ocr_retry_min_mean_conf", 50.0)):
        return True
    if weak_r > float(getattr(settings, "ocr_retry_max_weak_ratio", 0.40)):
        return True
    return False


def _tesseract_cfg(oem: int, psm: int, dpi: int) -> str:
    return f"--oem {oem} --psm {psm} -c user_defined_dpi={dpi}"


def _best_ocr_for_page(img_rgb, pytesseract_mod, min_chars: int, dpi: int, oem: int) -> str:
    """
    Strategie clara si eficienta:
    1. Determin profilul (clean/hard) din contrast
    2. Prima incercare: PSM 6 (bloc uniform) — cel mai bun pentru tabele medicale
    3. Daca calitate slaba: incerc PSM 4 (o coloana)
    4. Daca calitate inca slaba: incerc profilul opus
    5. Ultimul fallback: PSM 11 (sparse text)
    """
    lang = settings.ocr_lang
    # OEM 3 = LSTM pur (mai rapid + mai precis decat OEM 2 pe Tesseract 4/5)
    if oem == 2:
        oem = 3

    profile = _pick_profile(img_rgb)
    img_prep = _apply_profile(img_rgb, profile)
    alt_profile = "hard" if profile == "clean" else "clean"

    best_text = ""
    best_score = -1e9

    # PSM 6: bloc uniform de text — ideal pentru tabele cu randuri aliniate
    cfg6 = _tesseract_cfg(oem, 6, dpi)
    t, mc, wr, nw = _ocr_page_once(img_prep, lang, cfg6, pytesseract_mod)
    sc = _ocr_quality_score(t, mc, wr, nw, min_chars)
    if sc > best_score:
        best_text, best_score = t, sc

    if _needs_retry(best_text, mc, wr, nw, min_chars):
        # PSM 4: o singura coloana — unele buletine MedLife au margini
        cfg4 = _tesseract_cfg(oem, 4, dpi)
        t4, mc4, wr4, nw4 = _ocr_page_once(img_prep, lang, cfg4, pytesseract_mod)
        sc4 = _ocr_quality_score(t4, mc4, wr4, nw4, min_chars)
        if sc4 > best_score:
            best_text, best_score = t4, sc4

    if _needs_retry(best_text, mc, wr, nw, min_chars):
        # Profil opus pe PSM 6
        img_alt = _apply_profile(img_rgb, alt_profile)
        ta, mca, wra, nwa = _ocr_page_once(img_alt, lang, cfg6, pytesseract_mod)
        sca = _ocr_quality_score(ta, mca, wra, nwa, min_chars)
        if sca > best_score:
            best_text, best_score = ta, sca

        if _needs_retry(best_text, mca, wra, nwa, min_chars):
            # Fallback final: PSM 11 (sparse text — tabele fragmentate)
            cfg11 = _tesseract_cfg(oem, 11, dpi)
            t11, mc11, wr11, nw11 = _ocr_page_once(img_alt, lang, cfg11, pytesseract_mod)
            sc11 = _ocr_quality_score(t11, mc11, wr11, nw11, min_chars)
            if sc11 > best_score:
                best_text = t11

    return best_text


# ---------------------------------------------------------------------------
# Reconstructie randuri din TSV bbox (o singura trecere cu sweep liniar)
# ---------------------------------------------------------------------------

def _recluster_tsv_rows(df: dict, tolerance: int) -> str:
    """
    Reconstruieste randuri fizice din output-ul image_to_data (TSV cu bbox).
    Algoritm O(n log n): sorteaza dupa Y, parcurge o singura data.
    Returneaza text cu un rand per linie.
    """
    words = []
    n = len(df.get("text", []))
    for i in range(n):
        txt = (df["text"][i] or "").strip()
        if not txt:
            continue
        try:
            conf = int(df["conf"][i] or 0)
        except (ValueError, TypeError):
            conf = 0
        if conf < 20:
            continue
        try:
            x = int(df["left"][i])
            y = int(df["top"][i])
        except (ValueError, TypeError):
            continue
        words.append((y, x, txt))

    if not words:
        return ""

    words.sort()

    rows: list[list[tuple]] = []
    row_y: list[int] = []

    for y, x, txt in words:
        placed = False
        for ri in range(len(row_y) - 1, max(len(row_y) - 8, -1), -1):
            if abs(y - row_y[ri]) <= tolerance:
                rows[ri].append((x, txt))
                # Actualizeaza Y-ul reprezentativ al randului (medie rulanta simpla)
                row_y[ri] = (row_y[ri] + y) // 2
                placed = True
                break
        if not placed:
            rows.append([(x, txt)])
            row_y.append(y)

    lines = []
    for row in rows:
        row.sort(key=lambda w: w[0])
        line = " ".join(w[1] for w in row)
        if line.strip():
            lines.append(line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Trecere unica per pagina: render + TSV + string din acelasi image_to_data
# ---------------------------------------------------------------------------

def _ocr_page_full(page_pix_bytes: bytes, lang: str, oem: int, dpi: int,
                   pytesseract_mod, min_chars: int) -> Tuple[str, str]:
    """
    Dintr-un singur render de pagina produce:
    - text_string: textul OCR optimizat (pentru parser)
    - text_tsv: randuri reconstruite din coordonate bbox (backup pentru tabele 4-coloane)

    Returneaza (text_string, text_tsv).
    """
    from PIL import Image
    from pytesseract import Output
    import io

    img = Image.open(io.BytesIO(page_pix_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")

    # OEM 3 implicit
    if oem == 2:
        oem = 3

    # --- Text optimizat (cu preprocesare adaptiva) ---
    text_string = _best_ocr_for_page(img, pytesseract_mod, min_chars, dpi, oem)

    # --- TSV bbox pentru reconstructia randurilor (PSM 6, fara preprocesare agresiva) ---
    # Folosim imaginea curata (fara threshold) pentru TSV — coordonatele sunt mai precise
    cfg_tsv = _tesseract_cfg(oem, 6, dpi)
    try:
        profile = _pick_profile(img)
        img_light = _apply_profile(img, profile)
        df = pytesseract_mod.image_to_data(img_light, lang=lang, config=cfg_tsv,
                                           output_type=Output.DICT)
        # Toleranta = ~40% din inaltimea medie a unui caracter
        heights = [int(df["height"][i]) for i in range(len(df["text"]))
                   if (df["text"][i] or "").strip() and int(df.get("conf", [0])[i] or 0) >= 20]
        if heights:
            med_h = sorted(heights)[len(heights) // 2]
            tolerance = max(6, int(med_h * 0.40))
        else:
            tolerance = 12
        text_tsv = _recluster_tsv_rows(df, tolerance)
    except Exception:
        text_tsv = ""

    return text_string, text_tsv


def _run_ocr_all_pages(pdf_path: str) -> Tuple[str, str, str | None]:
    """
    Deschide PDF-ul O SINGURA DATA, randeaza fiecare pagina si ruleaza OCR.
    Returneaza (text_string_combined, text_tsv_combined, eroare_sau_None).
    """
    try:
        import fitz
    except ImportError:
        return "", "", "PyMuPDF nu este instalat. Ruleaza: pip install pymupdf"

    try:
        import pytesseract
    except ImportError:
        return "", "", "pytesseract nu este instalat. Ruleaza: pip install pytesseract"

    ok, err = tesseract_availability()
    if not ok:
        return "", "", err or "Tesseract OCR nu este disponibil."

    oem = getattr(settings, "ocr_oem", 3)
    min_chars = getattr(settings, "ocr_min_chars", 100)
    dpi = getattr(settings, "ocr_dpi_hint", 300)
    lang = settings.ocr_lang

    try:
        doc = fitz.open(pdf_path)
        strings = []
        tsvs = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            pix_bytes = pix.tobytes("png")

            try:
                ts, tv = _ocr_page_full(pix_bytes, lang, oem, dpi, pytesseract, min_chars)
            except Exception as pe:
                ts, tv = "", ""

            if ts.strip():
                strings.append(ts)
            if tv.strip():
                tsvs.append(tv)

        doc.close()
        return "\n".join(strings), "\n".join(tsvs), None
    except Exception as e:
        return "", "", f"Eroare la OCR: {e!s}"


# ---------------------------------------------------------------------------
# pdfplumber: extragere tabele bordate
# ---------------------------------------------------------------------------

def _extrage_tabele_pdfplumber(pdf_path: str) -> str:
    linii = []
    try:
        import pdfplumber as _pdfplumber
        with _pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tabele = page.extract_tables()
                for tabel in tabele:
                    for rand in tabel:
                        if not rand:
                            continue
                        celule = [str(c).strip() if c else "" for c in rand]
                        if not any(celule):
                            continue
                        linie = "  ".join(c for c in celule if c)
                        if linie:
                            linii.append(linie)
    except Exception:
        pass
    return "\n".join(linii)


# ---------------------------------------------------------------------------
# Valori colorate (PDF text — valori anormale)
# ---------------------------------------------------------------------------

def extract_colored_tokens(pdf_path: str) -> set:
    colored = set()
    try:
        import fitz
        doc = fitz.open(pdf_path)
        for page in doc:
            for block in page.get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("color", 0) != 0:
                            nums = re.findall(r'\d+[.,]\d+|\d+', span.get("text", ""))
                            colored.update(nums)
        doc.close()
    except Exception:
        pass
    return colored


# ---------------------------------------------------------------------------
# Entry point principal
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, str, str | None, set, str]:
    """
    Extrage text din PDF. Returneaza (text, tip, eroare_sau_None, colored_tokens, extractor).
    - tip = 'text'  — PDF cu text direct
    - tip = 'ocr'   — PDF scanat, s-a folosit Tesseract
    """
    min_chars = getattr(settings, "pdf_text_min_chars", 200)

    # --- Pas 1: PyMuPDF text direct ---
    text_fitz = ""
    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        for page in doc:
            try:
                text_fitz += page.get_text(sort=True) + "\n"
            except TypeError:
                text_fitz += page.get_text() + "\n"
        doc.close()
        text_fitz = (text_fitz or "").strip()
    except Exception:
        try:
            import fitz
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

    # Detecteaza rapid daca PDF-ul e scanat (text insignifiant)
    contine_numar = bool(re.search(r'\b\d+[.,]\d+\b|\b\d{2,}\b', text_fitz))
    este_text_pdf = len(text_fitz) >= min_chars and contine_numar
    if not este_text_pdf and len(text_fitz) >= min_chars * 2:
        este_text_pdf = True

    if este_text_pdf:
        # --- Pas 2 (doar pentru PDF text): pdfplumber pentru tabele bordate ---
        text_plumber = ""
        try:
            import pdfplumber as _pdfplumber
            with _pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_plumber += t + "\n"
        except Exception:
            pass
        text_tabele = _extrage_tabele_pdfplumber(pdf_path)
        text_plumber = (text_plumber or "").strip()
        if text_tabele:
            text_plumber = text_plumber + "\n" + text_tabele

        text_combinat = text_fitz
        extractor_used = "pymupdf"
        if text_plumber.strip():
            text_combinat = text_fitz + "\n" + text_plumber.strip()
            extractor_used = "pymupdf+pdfplumber"

        colored = extract_colored_tokens(pdf_path)
        return text_combinat, "text", None, colored, extractor_used

    # --- Pas 3: PDF scanat — o singura trecere OCR ---
    ocr_string, ocr_tsv, ocr_err = _run_ocr_all_pages(pdf_path)

    all_parts = [p for p in [text_fitz, ocr_string, ocr_tsv] if p.strip()]
    combined = "\n".join(all_parts)
    extractor = "ocr+tsv" if not text_fitz.strip() else "pymupdf+ocr+tsv"
    return combined, "ocr", ocr_err, set(), extractor
