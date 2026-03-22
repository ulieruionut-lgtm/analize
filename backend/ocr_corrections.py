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
    Corecții OCR pe linie înainte de parsare (organisme, fragmente de specii).
    Nu înlocuiește agresiv — doar pattern-uri frecvente din buletine reale.
    """
    if not linie or not linie.strip():
        return linie
    s = linie
    # Ha_emophi_!us → Haemophilus (variante OCR)
    s = re.sub(
        r"Ha[_\s]+emophi[_\s!l1Ii\*]*us",
        "Haemophilus",
        s,
        flags=re.IGNORECASE,
    )
    # Fragment «eriaceae» (lipsește Enterobact)
    s = re.sub(r"(?<![A-Za-zĂÂÎȘȚăâîșț])eriaceae\b", "Enterobacteriaceae", s, flags=re.IGNORECASE)
    s = re.sub(r"\bEntero\s*bacteriaceae\b", "Enterobacteriaceae", s, flags=re.IGNORECASE)
    # Moraxella catarrhalis
    s = re.sub(r"\bMoraxel{1,3}a\b", "Moraxella", s, flags=re.IGNORECASE)
    # Staphylococcus aureus cu zgomot
    s = re.sub(
        r"\bStaphylo[_\s]*coc\w*\s+aureus\b",
        "Staphylococcus aureus",
        s,
        flags=re.IGNORECASE,
    )
    # Clostridium difficile
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
