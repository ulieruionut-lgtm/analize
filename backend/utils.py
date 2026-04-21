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
    Prioritate: Data emitere -> Data buletin -> Data recoltare -> prima data valida.
    """
    if not text:
        return None
    patterns = [
        r"Data\s+emitere\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+buletin(?:ului)?\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+recoltare\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b",
        r"\b(\d{4}[./-]\d{2}[./-]\d{2})\b",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return normalizare_data_text(m.group(1))
    return None


def raspuns_eroare(status: int, mesaj: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"detail": mesaj[:500]},
        media_type="application/json",
    )
