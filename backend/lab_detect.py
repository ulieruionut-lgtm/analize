"""Detectare laborator din text PDF / nume fișier pentru matching pe catalog."""
from __future__ import annotations

import re
from typing import Optional, Tuple

# Sinonime frecvente în PDF care nu coincid exact cu `laboratoare.nume`
_TEXT_ALIASES: list[tuple[str, str]] = [
    (r"med\s*life|medlife|policlinic[ăa]?\s+.*pdr", "MedLife"),
    (r"bioclinica", "Bioclinica"),
    (r"synevo|synlab", "Synevo"),
    (r"regina\s+maria|reginamaria|hospital\s+regina", "Regina Maria"),
    (r"medicover", "Medicover"),
    (r"cerba\s+healthcare|cerba", "Cerba"),
    (r"unilabs", "Unilabs"),
]


def _normalize_cmp(s: str) -> str:
    t = (s or "").lower()
    t = re.sub(r"[\s\-_\.]+", "", t)
    return t


def _detect_nume_from_text(text: str) -> Optional[str]:
    """Returnează nume canonic (ex. MedLife) dacă găsește pattern în primele ~15k caractere."""
    if not text or len(text.strip()) < 12:
        return None
    head = text[:15000]
    head_cmp = _normalize_cmp(head)
    best: Optional[str] = None
    best_key_len = 0
    for pattern, canonical in _TEXT_ALIASES:
        if re.search(pattern, head, flags=re.IGNORECASE):
            k = _normalize_cmp(canonical)
            if len(k) > best_key_len:
                best_key_len = len(k)
                best = canonical
    # Fallback: nume proprii lungi din text (ex. titlu buletin)
    if best is None and "bioclinica" in head_cmp:
        return "Bioclinica"
    return best


def _detect_from_filename(filename: Optional[str]) -> Optional[str]:
    if not filename:
        return None
    low = filename.lower()
    for _pat, canonical in _TEXT_ALIASES:
        c = canonical.lower().replace(" ", "")
        if c in low.replace(" ", "").replace("_", ""):
            return canonical
    return None


def enumerate_lab_brand_mentions(text: str) -> list[dict]:
    """
    Caută mărci/rețele de laborator în **tot** textul (nu doar antetul).

    Utile când un PDF conține mai multe buletine sau anteturi repetate: vezi
    apariții multiple sau două rețele diferite — `resolve_laborator_id_for_text`
    folosește doar începutul documentului pentru potrivire automată.
    """
    if not text or len(text.strip()) < 8:
        return []
    by_canon: dict[str, list[int]] = {}
    for pattern, canonical in _TEXT_ALIASES:
        try:
            for m in re.finditer(pattern, text, flags=re.IGNORECASE):
                by_canon.setdefault(canonical, []).append(m.start())
        except re.error:
            continue
    out: list[dict] = []
    for canon in sorted(by_canon.keys()):
        pos = sorted(by_canon[canon])
        out.append(
            {
                "laborator": canon,
                "aparitii": len(pos),
                "prima_pozitie_caracter": pos[0],
                "ultima_pozitie_caracter": pos[-1],
            }
        )
    return out


def resolve_laborator_id_for_text(
    text: str,
    filename: Optional[str] = None,
    *,
    laborator_id_override: Optional[int] = None,
    laborator_name_override: Optional[str] = None,
) -> Tuple[Optional[int], Optional[str]]:
    """
    Returnează (laborator_id, nume_laborator) pentru normalizare și câmpul `buletine.laborator`.

    Prioritate: ID explicit > nume explicit > text PDF > nume fișier.
    Dacă tabelele lipsesc sau nu există potrivire, (None, None) — fluxul vechi rămâne neschimbat.
    """
    try:
        from backend.database import get_laboratoare
    except Exception:
        return None, None

    try:
        labs = get_laboratoare()
    except Exception:
        labs = []

    if not labs:
        return None, None

    by_id = {int(l["id"]): l for l in labs if l.get("id") is not None}

    if laborator_id_override is not None:
        try:
            lid = int(laborator_id_override)
        except (TypeError, ValueError):
            lid = None
        if lid is not None:
            row = by_id.get(lid)
            if row:
                return lid, (row.get("nume") or "").strip() or None

    if laborator_name_override and str(laborator_name_override).strip():
        wanted = str(laborator_name_override).strip().lower()
        best_row = None
        best_score = 0
        for lab in labs:
            nume = (lab.get("nume") or "").strip()
            if not nume:
                continue
            nl = nume.lower()
            score = 0
            if nl == wanted:
                score = 100 + len(nl)
            elif nl.startswith(wanted) or wanted.startswith(nl):
                score = 50 + min(len(nl), len(wanted))
            elif wanted in nl or nl in wanted:
                score = 20 + min(len(nl), len(wanted))
            if score > best_score:
                best_score = score
                best_row = lab
        if best_row and best_score >= 20:
            return int(best_row["id"]), (best_row.get("nume") or "").strip()

    canonical = _detect_nume_from_text(text) or _detect_from_filename(filename)
    if not canonical:
        # Potrivire după nume înregistrat în DB (cel mai lung nume inclus în text)
        head = (text or "")[:12000].lower()
        head_ns = re.sub(r"\s+", "", head)
        best_id = None
        best_len = 0
        for lab in labs:
            nume = (lab.get("nume") or "").strip()
            if len(nume) < 4:
                continue
            nl = nume.lower()
            ncompact = nl.replace(" ", "")
            if nl in head or ncompact in head_ns:
                if len(nume) >= best_len:
                    best_len = len(nume)
                    best_id = int(lab["id"])
        if best_id is not None:
            row = by_id.get(best_id)
            return best_id, (row.get("nume") or "").strip() if row else (best_id, None)
        return None, None

    # Mapare canonical -> rând din DB
    cnorm = _normalize_cmp(canonical)
    for lab in labs:
        nume = (lab.get("nume") or "").strip()
        if not nume:
            continue
        if _normalize_cmp(nume) == cnorm or canonical.lower() in nume.lower():
            return int(lab["id"]), nume
        retea = (lab.get("retea") or "").strip()
        if retea and canonical.lower() == retea.lower():
            return int(lab["id"]), nume
    return None, None
