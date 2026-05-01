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
- Optional: randuri din structura Tesseract (block/line) + goluri largi intre „coloane” (settings)
"""
import logging
import os
import platform
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Tuple

from backend.config import settings

_log = logging.getLogger(__name__)

# Evităm re-probing la fiecare upload
_tesseract_cmd_last: str | None = None


def _apply_tesseract_executable() -> None:
    """
    Setează pytesseract.pytesseract.tesseract_cmd dacă executabilul nu e în PATH.
    Windows: probă locațiile standard UB-Mannheim. Env TESSERACT_CMD are prioritate.
    """
    global _tesseract_cmd_last
    try:
        import pytesseract
    except ImportError:
        return

    if shutil.which("tesseract"):
        _tesseract_cmd_last = "PATH"
        return

    cand = (os.environ.get("TESSERACT_CMD") or "").strip()
    if not cand:
        cfg = getattr(settings, "tesseract_cmd", None)
        if cfg:
            cand = str(cfg).strip()
    if cand and Path(cand).is_file():
        pytesseract.pytesseract.tesseract_cmd = cand
        _tesseract_cmd_last = cand
        _log.info("[OCR] Tesseract din TESSERACT_CMD / setări: %s", cand)
        return

    if platform.system() == "Windows":
        for p in (
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        ):
            if p.is_file():
                pytesseract.pytesseract.tesseract_cmd = str(p)
                _tesseract_cmd_last = str(p)
                _log.info("[OCR] Tesseract detectat (Windows implicit): %s", p)
                return


# ---------------------------------------------------------------------------
# Verificare disponibilitate Tesseract
# ---------------------------------------------------------------------------

def tesseract_availability() -> Tuple[bool, str | None]:
    try:
        import pytesseract
    except ImportError:
        return False, "pytesseract nu este instalat. Ruleaza: pip install pytesseract"

    _apply_tesseract_executable()

    tess_prefix = getattr(settings, "tessdata_prefix", None)
    if tess_prefix:
        os.environ["TESSDATA_PREFIX"] = str(tess_prefix)

    try:
        pytesseract.get_tesseract_version()
        return True, None
    except Exception as tess_err:
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
# Detectare pagini grafice (evolutie Regina Maria)
# ---------------------------------------------------------------------------

def _este_pagina_grafice(page_fitz) -> bool:
    """
    Detecteaza paginile de evolutie grafica din buletine Regina Maria.
    Aceste pagini contin mesajul 'Draga ... iata evolutia in timp a analizelor tale'.
    Detectia se bazeaza EXCLUSIV pe markeri textuali expliciti — nu pe heuristici
    bazate pe numar de cuvinte / blocuri imagine (ar elimina pagini scanate valide).
    """
    try:
        text = page_fitz.get_text() or ""
        text_lower = text.lower()
        if "evolutia in timp" in text_lower:
            return True
        if "iata evolutia" in text_lower:
            return True
        if "draga " in text_lower and "analiz" in text_lower:
            return True
    except Exception:
        pass
    return False


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
    letters = sum(1 for ch in text if ch.isalpha())
    digits = sum(1 for ch in text if ch.isdigit())
    spaces = sum(1 for ch in text if ch.isspace())
    punct = max(0, L - letters - digits - spaces)
    letter_ratio = (letters / L) if L else 0.0
    punct_ratio = (punct / L) if L else 0.0

    score = mean_c * 0.45
    score += min(L / 8.0, 45.0)
    score -= weak_r * 38.0
    if L < min_chars:
        score -= (min_chars - L) * 0.55
    if n_words == 0 and L > 5:
        score -= 15.0
    # Penalizeaza textul "zgomot" (multe simboluri/punctuatie, putine litere).
    if L >= 140 and letter_ratio < 0.42:
        score -= (0.42 - letter_ratio) * 95.0
    if L >= 140 and punct_ratio > 0.22:
        score -= (punct_ratio - 0.22) * 110.0
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


def _best_ocr_for_page(
    img_rgb, pytesseract_mod, min_chars: int, dpi: int, oem: int
) -> Tuple[str, Dict[str, Any], str]:
    """
    Strategie clara si eficienta:
    1. Determin profilul (clean/hard) din contrast
    2. Prima incercare: PSM 6 (bloc uniform) — cel mai bun pentru tabele medicale
    3. Daca calitate slaba: incerc PSM 4 (o coloana)
    4. Daca calitate inca slaba: incerc profilul opus
    5. Ultimul fallback: PSM 11 (sparse text)

    Returnează (text, meta, lang_efectiv). Dacă OCR cu limba configurată e aproape gol,
    reîncearcă cu «eng» (ex.: lipsește traineddata pentru «ron»).
    """
    primary = (getattr(settings, "ocr_lang", None) or "ron+eng").strip() or "eng"
    # OEM 3 = LSTM pur (mai rapid + mai precis decat OEM 2 pe Tesseract 4/5)
    if oem == 2:
        oem = 3

    profile = _pick_profile(img_rgb)
    img_prep = _apply_profile(img_rgb, profile)
    alt_profile = "hard" if profile == "clean" else "clean"

    img_alt = _apply_profile(img_rgb, alt_profile)
    candidates = [
        (img_prep, profile, 6),
        (img_prep, profile, 4),
        (img_alt, alt_profile, 6),
        (img_alt, alt_profile, 11),
    ]

    def _run_candidates(lang_try: str) -> Tuple[str, float, Dict[str, Any]]:
        best_text_l = ""
        best_score_l = -1e9
        best_meta_l: Dict[str, Any] = {
            "mean_conf": 0.0,
            "weak_ratio": 1.0,
            "n_words": 0,
            "score": -1e9,
            "profile": profile,
            "psm": 6,
        }
        for img_try, prof_try, psm_try in candidates:
            cfg = _tesseract_cfg(oem, psm_try, dpi)
            t, mc, wr, nw = _ocr_page_once(img_try, lang_try, cfg, pytesseract_mod)
            sc = _ocr_quality_score(t, mc, wr, nw, min_chars)
            if sc > best_score_l:
                best_text_l, best_score_l = t, sc
                best_meta_l = {
                    "mean_conf": round(float(mc), 2),
                    "weak_ratio": round(float(wr), 4),
                    "n_words": int(nw),
                    "score": round(float(sc), 2),
                    "profile": prof_try,
                    "psm": psm_try,
                }
        return best_text_l, best_score_l, best_meta_l

    best_text, best_score, best_meta = _run_candidates(primary)
    len_prim = len((best_text or "").strip())
    if len_prim < max(45, min_chars // 2) and primary.lower() != "eng":
        t_eng, sc_eng, meta_eng = _run_candidates("eng")
        if len((t_eng or "").strip()) > len_prim:
            best_meta = {**meta_eng, "lang_fallback": "eng"}
            return t_eng, best_meta, "eng"
    return best_text, best_meta, primary


# ---------------------------------------------------------------------------
# Reconstructie randuri din TSV bbox (o singura trecere cu sweep liniar)
# ---------------------------------------------------------------------------

def _line_with_column_gaps(
    words: list[tuple[int, str, int]],
    *,
    gap_mult: float = 3.5,
    min_gap_px: int = 18,
) -> str:
    """
    Intra-o singura linie vizuala: daca distanta orizontala intre cuvinte e mare,
    insereaza tab-uri (gol vizibil) — ajuta parserul sa vada analit | valoare | unitate.
    """
    if not words:
        return ""
    words = sorted(words, key=lambda w: w[0])
    if len(words) == 1:
        return words[0][1]
    gaps: list[int] = []
    for i in range(len(words) - 1):
        l1, _t1, w1 = words[i]
        l2, _t2, _w2 = words[i + 1]
        gaps.append(max(0, l2 - (l1 + w1)))
    med = sorted(gaps)[len(gaps) // 2] if gaps else 0
    thr = max(min_gap_px, int(med * gap_mult + 0.5))
    parts = [words[0][1]]
    for i in range(len(gaps)):
        sep = " \t " if gaps[i] >= thr else " "
        parts.append(sep + words[i + 1][1])
    return "".join(parts)


def _layout_lines_tesseract_blocks(df: dict, *, use_column_gaps: bool) -> str:
    """
    Grupare dupa block_num / par_num / line_num (output Tesseract), cuvinte sortate pe X.
    Mai stabila decat doar clusterizare Y pentru multe buletine cu tabele.
    """
    n = len(df.get("text", []))
    if n == 0:
        return ""
    levels = df.get("level", [])
    texts = df.get("text", [])
    confs = df.get("conf", [])
    blocks = df.get("block_num", [0] * n)
    pars = df.get("par_num", [0] * n)
    lines_n = df.get("line_num", [0] * n)
    lefts = df.get("left", [0] * n)
    widths = df.get("width", [0] * n)

    groups: dict[tuple[int, int, int], list[tuple[int, str, int]]] = {}
    for i in range(n):
        try:
            if int(levels[i]) != 5:
                continue
        except (ValueError, TypeError, IndexError):
            continue
        txt = (texts[i] or "").strip()
        if not txt:
            continue
        try:
            conf = int(confs[i] or 0)
        except (ValueError, TypeError):
            conf = 0
        if conf < 20:
            continue
        try:
            b = int(blocks[i])
            p = int(pars[i])
            ln = int(lines_n[i])
            lx = int(lefts[i])
            wd = int(widths[i]) if i < len(widths) else 0
        except (ValueError, TypeError, IndexError):
            continue
        groups.setdefault((b, p, ln), []).append((lx, txt, max(wd, 1)))

    out_lines: list[str] = []
    for key in sorted(groups.keys()):
        wlist = groups[key]
        if use_column_gaps:
            line = _line_with_column_gaps(wlist)
        else:
            wlist.sort(key=lambda w: w[0])
            line = " ".join(w[1] for w in wlist)
        if line.strip():
            out_lines.append(line)
    return "\n".join(out_lines)


def _count_tsv_words(df: dict) -> int:
    n = len(df.get("text", []))
    levels = df.get("level", [])
    texts = df.get("text", [])
    confs = df.get("conf", [])
    c = 0
    for i in range(n):
        try:
            if int(levels[i]) != 5:
                continue
        except (ValueError, TypeError, IndexError):
            continue
        if not (texts[i] or "").strip():
            continue
        try:
            if int(confs[i] or 0) < 20:
                continue
        except (ValueError, TypeError):
            continue
        c += 1
    return c


def _choose_tsv_layout_text(df: dict, tolerance: int, *, use_column_gaps: bool) -> str:
    """
    Combina structura Tesseract (block/line) cu fallback la clusterizare Y existenta,
    cand structurat pare sa fi „lipit” prea multe randuri pe verticala.
    """
    structured = _layout_lines_tesseract_blocks(df, use_column_gaps=use_column_gaps)
    legacy = _recluster_tsv_rows(df, tolerance)
    sl = len([x for x in structured.splitlines() if x.strip()])
    ll = len([x for x in legacy.splitlines() if x.strip()])
    nw = _count_tsv_words(df)
    if not structured.strip():
        return legacy
    # Prea putine linii fata de numarul de cuvinte => probabil randuri de tabel lipite
    if nw > 0 and sl < max(4, nw // 12) and ll > sl * 1.35:
        return legacy
    if ll > sl * 2 and ll > 8 and nw > 20:
        return legacy
    return structured


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

def _ocr_page_full(
    page_pix_bytes: bytes, oem: int, dpi: int, pytesseract_mod, min_chars: int
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Dintr-un singur render de pagina produce:
    - text_string: textul OCR optimizat (pentru parser)
    - text_tsv: randuri reconstruite din coordonate bbox (backup pentru tabele 4-coloane)

    Returneaza (text_string, text_tsv, page_metrics).
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
    text_string, page_metrics, lang_eff = _best_ocr_for_page(
        img, pytesseract_mod, min_chars, dpi, oem
    )
    page_metrics = {**page_metrics, "ocr_lang": lang_eff}

    # --- TSV bbox pentru reconstructia randurilor (PSM 6, fara preprocesare agresiva) ---
    # Folosim imaginea curata (fara threshold) pentru TSV — coordonatele sunt mai precise
    cfg_tsv = _tesseract_cfg(oem, 6, dpi)
    try:
        profile = _pick_profile(img)
        img_light = _apply_profile(img, profile)
        df = pytesseract_mod.image_to_data(
            img_light, lang=lang_eff, config=cfg_tsv, output_type=Output.DICT
        )
        # Toleranta = ~40% din inaltimea medie a unui caracter
        heights = [int(df["height"][i]) for i in range(len(df["text"]))
                   if (df["text"][i] or "").strip() and int(df.get("conf", [0])[i] or 0) >= 20]
        if heights:
            med_h = sorted(heights)[len(heights) // 2]
            tolerance = max(6, int(med_h * 0.40))
        else:
            tolerance = 12
        use_gaps = bool(getattr(settings, "ocr_column_segmentation", False))
        if getattr(settings, "ocr_layout_auto", True):
            text_tsv = _choose_tsv_layout_text(df, tolerance, use_column_gaps=use_gaps)
        else:
            text_tsv = _recluster_tsv_rows(df, tolerance)
    except Exception:
        text_tsv = ""

    return text_string, text_tsv, page_metrics


def _run_ocr_all_pages(pdf_path: str, dpi_override: int | None = None) -> Tuple[str, str, str | None, Dict[str, Any]]:
    """
    Deschide PDF-ul O SINGURA DATA, randeaza fiecare pagina si ruleaza OCR.
    Returneaza (text_string_combined, text_tsv_combined, eroare_sau_None).
    """
    try:
        import fitz
    except ImportError:
        return "", "", "PyMuPDF nu este instalat. Ruleaza: pip install pymupdf", {}

    try:
        import pytesseract
    except ImportError:
        return "", "", "pytesseract nu este instalat. Ruleaza: pip install pytesseract", {}

    ok, err = tesseract_availability()
    if not ok:
        return "", "", err or "Tesseract OCR nu este disponibil.", {}

    oem = getattr(settings, "ocr_oem", 3)
    min_chars = getattr(settings, "ocr_min_chars", 100)
    dpi = int(dpi_override) if dpi_override is not None else int(getattr(settings, "ocr_dpi_hint", 300))

    try:
        doc = fitz.open(pdf_path)
        strings = []
        tsvs = []
        per_page: list[Dict[str, Any]] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            if _este_pagina_grafice(page):
                _log.info("[OCR_SKIP] Pagina %d/%d - grafic evolutie, sarire.", page_num + 1, len(doc))
                continue
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            pix_bytes = pix.tobytes("png")

            try:
                ts, tv, pm = _ocr_page_full(pix_bytes, oem, dpi, pytesseract, min_chars)
            except Exception as pe:
                _log.warning("[OCR_PAGE_FAIL] Pagina %d/%d: %s", page_num + 1, len(doc), str(pe)[:200])
                ts, tv, pm = "", "", {}

            if ts.strip():
                strings.append(ts)
            if tv.strip():
                tsvs.append(tv)
            if pm:
                per_page.append(
                    {
                        "page": page_num + 1,
                        "mean_conf": pm.get("mean_conf", 0.0),
                        "weak_ratio": pm.get("weak_ratio", 1.0),
                        "n_words": pm.get("n_words", 0),
                        "score": pm.get("score", -1e9),
                        "profile": pm.get("profile"),
                        "psm": pm.get("psm"),
                    }
                )

        doc.close()
        if per_page:
            avg_conf = sum(float(p.get("mean_conf", 0.0)) for p in per_page) / len(per_page)
            avg_weak = sum(float(p.get("weak_ratio", 1.0)) for p in per_page) / len(per_page)
            avg_score = sum(float(p.get("score", 0.0)) for p in per_page) / len(per_page)
            ocr_metrics: Dict[str, Any] = {
                "pages": per_page,
                "summary": {
                    "pages_count": len(per_page),
                    "avg_mean_conf": round(avg_conf, 2),
                    "avg_weak_ratio": round(avg_weak, 4),
                    "avg_score": round(avg_score, 2),
                },
            }
        else:
            ocr_metrics = {"pages": [], "summary": {"pages_count": 0, "avg_mean_conf": 0.0, "avg_weak_ratio": 1.0, "avg_score": 0.0}}
        return "\n".join(strings), "\n".join(tsvs), None, ocr_metrics
    except Exception as e:
        return "", "", f"Eroare la OCR: {e!s}", {}


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
                        # Sare prima coloana daca e numar/numar zecimal (Nr. din tabele TEO HEALTH)
                        # si a doua coloana incepe cu o litera (= Denumire test, nu valoare)
                        if (celule and re.match(r'^\d+(?:\.\d+)*$', celule[0])
                                and len(celule) > 1 and celule[1]
                                and re.match(r'[A-Za-zĂÂÎȘȚăâîșț*\u0100-\u017F]', celule[1])):
                            celule = celule[1:]
                        if not celule:
                            continue
                        # Ia maxim primele 3 coloane (Denumire, Rezultat, UM) — sare Interval (redundant)
                        celule = celule[:3]
                        parts = [c for c in celule if c]
                        if not parts:
                            continue
                        linie = " ".join(parts)
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

def extract_text_from_pdf(pdf_path: str, include_metrics: bool = False, dpi_override: int | None = None):
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
            if _este_pagina_grafice(page):
                continue
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
                if _este_pagina_grafice(page):
                    continue
                try:
                    text_fitz += page.get_text(sort=True) + "\n"
                except TypeError:
                    text_fitz += page.get_text() + "\n"
            doc.close()
            text_fitz = (text_fitz or "").strip()
        except Exception:
            pass

    # --- Pas 2: pdfplumber text + tabele (indiferent de tip PDF) ---
    # pdfplumber/pdfminer reuseste uneori sa extraga text din PDF-uri cu fonturi nestandard
    # unde PyMuPDF esueaza. Incercam INTOTDEAUNA — daca reuseste, evitam OCR.
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
        # Tabele inainte de text plain: parserul vede coloanele curate inainte de text duplicat
        text_plumber = text_tabele + "\n" + text_plumber if text_plumber else text_tabele

    # Detecteaza rapid daca PDF-ul e scanat (text insignifiant din AMBELE surse)
    text_all_available = text_fitz + "\n" + text_plumber
    contine_numar = bool(re.search(r'\b\d+[.,]\d+\b|\b\d{2,}\b', text_all_available))
    este_text_pdf = len(text_all_available.strip()) >= min_chars and contine_numar
    if not este_text_pdf and len(text_all_available.strip()) >= min_chars * 2:
        este_text_pdf = True

    if este_text_pdf:
        # --- PDF cu text suficient: combina PyMuPDF + pdfplumber (tabele primele) ---
        parts_text = [p for p in [text_tabele, text_fitz, text_plumber] if p.strip()]
        text_combinat = "\n".join(parts_text)
        extractor_used = "pymupdf" if not text_plumber.strip() else "pdfplumber+pymupdf"
        if text_tabele.strip():
            extractor_used = "pdfplumber-tables+" + extractor_used

        colored = extract_colored_tokens(pdf_path)
        result = (text_combinat, "text", None, colored, extractor_used)
        if include_metrics:
            return result + ({},)
        return result

    # --- Pas 3: PDF scanat — o singura trecere OCR ---
    # Adaugam si orice text pdfplumber a reusit sa extraga (poate partial)
    ocr_string, ocr_tsv, ocr_err, ocr_metrics = _run_ocr_all_pages(pdf_path, dpi_override=dpi_override)

    # pdfplumber tabele PRIMELE — in caz de dedup, rezultatele curate din tabele castiga
    all_parts = [p for p in [text_tabele, text_plumber, text_fitz, ocr_string, ocr_tsv] if p.strip()]
    combined = "\n".join(all_parts)
    extractor = "ocr+tsv" if not text_fitz.strip() else "pymupdf+ocr+tsv"
    if text_tabele.strip():
        extractor = "pdfplumber-tables+" + extractor
    result = (combined, "ocr", ocr_err, set(), extractor)
    if include_metrics:
        return result + (ocr_metrics,)
    return result


def extract_text_with_metrics(pdf_path: str, dpi_override: int | None = None):
    """Compat helper: aceleași date ca extract_text_from_pdf + ocr_metrics."""
    return extract_text_from_pdf(pdf_path, include_metrics=True, dpi_override=dpi_override)
