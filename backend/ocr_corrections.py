"""
Corecții OCR partajate între normalizer (mapare alias) și parser (chei deduplicare).

Aplică pe text deja normalizat (lowercase, fără diacritice) sau pe fragmente de linie,
conform contextului apelantului.
"""
import re
from typing import Tuple

# (pattern, înlocuire) — `raw_norm` din normalizer (după _normalizeaza)
OCR_FIX_PATTERNS_NORMALIZAT: Tuple[Tuple[str, str], ...] = (
    (r"\bumar\b", "numar"),  # N citit greșit ca u
    (r"\bcrealinin[ae]?\b", "creatinina"),
    (r"\bglu[o0]{2,}za\b", "glucoza"),
    (r"\bhemoglo[b6]ina\b", "hemoglobina"),
    (r"\bh[ce]moglobina\b", "hemoglobina"),
    (r"\bhemat[o0]crit\b", "hematocrit"),
    (r"\bleuc[o0]cite\b", "leucocite"),
    (r"\btr[o0]mbocite\b", "trombocite"),
    (r"\bferit[i1]na\b", "feritina"),
    (r"\bcolester[o0]l\b", "colesterol"),
    (r"\btriglicer[i1]de\b", "trigliceride"),
    (r"\berit[ro]cite\b", "eritrocite"),
    (r"pla\.?\s*chetar", "plachetar"),
    (r"tranzmonale", "tranzitionale"),
    (r"tranzutlonale", "tranzitionale"),
    # Microbiologie — după normalizare (lowercase, fără diacritice)
    (r"\bha[_\s]*emophi[_\s!l1i]*us\b", "haemophilus"),
    (r"\bhaemophilus\s+influenz\w*\b", "haemophilus influenzae"),
    (r"^\s*eriaceae\b", "enterobacteriaceae"),
    (r"\s+eriaceae\b", " enterobacteriaceae"),
    (r"\bentero\s*bacteriaceae\b", "enterobacteriaceae"),
    (r"\bmoraxel{1,3}a\b", "moraxella"),
    (r"\bstaphylo[_\s]*coc\w*\s+aureus\b", "staphylococcus aureus"),
    (r"\bclostridi\w*\s+difficile\b", "clostridium difficile"),
    (r"\bdiagnostipz\b", "diagnostic"),
    (r"\bdiagn[o0]stipz\b", "diagnostic"),
)


def corecteaza_ocr_linie_buletin(linie: str) -> str:
    """
    Corecții OCR pe linie înainte de parsare.
    Nu înlocuiește agresiv — doar pattern-uri frecvente din buletine reale.
    """
    if not linie or not linie.strip():
        return linie
    s = linie

    # --- Simboluri parazite între denumire și valoare (MedLife scanat) ---
    # "TSH ¢ 2.88" → "TSH 2.88"  |  "TSH * 2.88" → "TSH 2.88"
    # Simboluri: ¢ § ° ~ ` ^ ± ∓ † ‡ ¶ și combinații cu spații
    s = re.sub(r"(?<=\s)[¢§°~`^±†‡¶]+(?=\s)", "", s)
    # "TSH¢2.88" (fără spații) → "TSH 2.88"
    s = re.sub(r"([A-Za-z])[¢§°~`^±†‡¶]+(\d)", r"\1 \2", s)

    # --- Unități OCR corupte (MedLife, Synevo scanat) ---
    # pmoliL / pmolil / pmoll → pmol/L  (cu sau fara spatiu inaintea unitatii)
    s = re.sub(r"\bpmoli?[lL]\b", "pmol/L", s)
    s = re.sub(r"(\d)pmoli?[lL]?\b", r"\1 pmol/L", s)  # "230pmoli" → "230 pmol/L"
    # uUl/mt / uUI/mt / uUl/mL → uUI/mL (TSH)
    s = re.sub(r"\bu[Uu][Ii]?/m[tTlL]\b", "uUI/mL", s, flags=re.IGNORECASE)
    # mUl/ml / mUI/ml → mUI/mL
    s = re.sub(r"\bm[Uu][Ii]?/m[lL]\b", "mUI/mL", s, flags=re.IGNORECASE)
    # *10%6 / *10'6 / *106 → *10^6  (eritrocite MedLife)
    s = re.sub(r"\*10[%\'`]6", "*10^6", s)
    # *10'3 / *10%3 / *103 → *10^3
    s = re.sub(r"\*10[%\'`]3", "*10^3", s)
    # *1073 / *1075 / *1073 (OCR confundă ^ cu 7) → *10^3
    s = re.sub(r"\*107([3-6])", r"*10^\1", s)
    # ng/mL scris ca ng/ml (normalizare minora)
    # pUlimL / pUliml → pUI/mL (TSH interval)
    s = re.sub(r"\bp[Uu]l?i?m[lL]\b", "pUI/mL", s)

    # mg/di → mg/dL (OCR confundă L cu i)
    s = re.sub(r"\bmg/di\b", "mg/dL", s, flags=re.IGNORECASE)
    # mgl/di / mgl/dl → mg/dL
    s = re.sub(r"\bmgl?/d[il]\b", "mg/dL", s, flags=re.IGNORECASE)
    # IU/ml → UI/mL (normalizare)
    # UL → U/L (Tesseract pierde bara oblică)
    s = re.sub(r"(?<=\d)\s+UL\b", " U/L", s)
    s = re.sub(r"\bUL\b(?=\s*<)", "U/L", s)

    # --- Microbiologie: organisme corupte ---
    s = re.sub(
        r"Ha[_\s]+emophi[_\s!l1Ii\*]*us",
        "Haemophilus",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(r"(?<![A-Za-zĂÂÎȘȚăâîșț])eriaceae\b", "Enterobacteriaceae", s, flags=re.IGNORECASE)
    s = re.sub(r"\bEntero\s*bacteriaceae\b", "Enterobacteriaceae", s, flags=re.IGNORECASE)
    s = re.sub(r"\bMoraxel{1,3}a\b", "Moraxella", s, flags=re.IGNORECASE)
    s = re.sub(
        r"\bStaphylo[_\s]*coc\w*\s+aureus\b",
        "Staphylococcus aureus",
        s,
        flags=re.IGNORECASE,
    )
    s = re.sub(
        r"\bClostridi\w*\s+difficile\b",
        "Clostridium difficile",
        s,
        flags=re.IGNORECASE,
    )
    return s


def aplică_corectii_ocr_normalizat(raw_norm: str) -> str:
    """Aplică înlocuiri tip OCR pe string normalizat (alias matching)."""
    out = raw_norm
    for pattern, repl in OCR_FIX_PATTERNS_NORMALIZAT:
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    return out


def corecteaza_umar_numar_in_denumire(s: str) -> str:
    """
    Înlocuiește «umar de» → «numar de» pentru deduplicare / chei (lowercase).
    Folosit de parser la _key_denumire.
    """
    if not s:
        return s
    return re.sub(r"\bumar\s+de\b", "numar de", s, flags=re.IGNORECASE)


def corecteaza_umar_numar_artefact_capitalizat(text: str) -> str:
    """
    Varianta pentru denumiri afișate: «Umar de» → «Numar de» (ca în laborator).
    Folosit de normalizer._curata_artefacte.
    """
    if not text:
        return text
    return re.sub(r"\bumar\s+de\b", "Numar de", text, flags=re.IGNORECASE)
