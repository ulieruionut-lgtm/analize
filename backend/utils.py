"""Utilitare partajate: formatare date, extragere data buletin, raspunsuri eroare."""
import re
from typing import Optional

from fastapi.responses import JSONResponse


def normalizare_data_text(raw: str) -> str:
    """Normalizeaza data in format ISO YYYY-MM-DD (compatibil PostgreSQL)."""
    raw = (raw or "").strip()
    raw = raw.replace("/", ".").replace("-", ".")
    # DD.MM.YYYY -> YYYY-MM-DD
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # YYYY.MM.DD -> YYYY-MM-DD
    m = re.match(r"^(\d{4})\.(\d{2})\.(\d{2})$", raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return raw[:10]


def extrage_data_buletin(text: str) -> Optional[str]:
    """
    Extrage data reala din buletin (fara ora).
    Prioritate: Data eliberarii / emitere / buletin -> Data recoltarii -> prima data valida
    (excludem Data nasterii / Data inregistrarii care nu sunt date ale buletinului).
    """
    if not text:
        return None
    # Patternuri cu etichetă explicită — ordonate de la cea mai specifică la mai generală
    labeled = [
        r"Data\s+eliber[aă]rii\s+rezultat(?:ului)?\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+emitere\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+buletin(?:ului)?\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+recoltarii?\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+recoltare\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+receptiei?\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+inregistrarii?\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
    ]
    for pat in labeled:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return normalizare_data_text(m.group(1))
    # Fallback: prima dată DD.MM.YYYY care NU apare după "Data nasterii" / "nasterii"
    # Înlocuim orice segment "Data nasterii: XX.XX.XXXX" înainte de căutare
    text_fara_nastere = re.sub(
        r"Data\s+nasterii\s*[:\-]?\s*\d{2}[./-]\d{2}[./-]\d{4}", "", text, flags=re.IGNORECASE
    )
    text_fara_nastere = re.sub(
        r"nasterii\s+\d{2}[./-]\d{2}[./-]\d{4}", "", text_fara_nastere, flags=re.IGNORECASE
    )
    m = re.search(r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b", text_fara_nastere)
    if m:
        return normalizare_data_text(m.group(1))
    m = re.search(r"\b(\d{4}[./-]\d{2}[./-]\d{2})\b", text_fara_nastere)
    if m:
        return normalizare_data_text(m.group(1))
    return None


def raspuns_eroare(status: int, mesaj: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"detail": mesaj[:500]},
        media_type="application/json",
    )


def buletin_data_to_iso(val) -> str:
    """Normalizează data_buletin din DB sau text la YYYY-MM-DD pentru comparare."""
    if val is None:
        return ""
    s = str(val).strip()
    if not s:
        return ""
    if "T" in s:
        s = s.split("T")[0]
    elif " " in s and len(s) > 10 and ":" in s:
        s = s.split(" ")[0]
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return normalizare_data_text(s)
