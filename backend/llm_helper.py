import json
import logging
from typing import Any, Dict, List, Optional

from rapidfuzz import fuzz, process

from backend.llm_chat import chat_completion_system_user, suggest_alias_llm_configured

_log = logging.getLogger(__name__)


def suggest_alias_from_llm(
    denumire_raw: str,
    snippets: Optional[List[str]] = None,
    categorie_pdf: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Returneaza sugestii de alias din LLM pentru denumire necunoscuta.

    Returneaza lista de dict-uri cu cheile 'analiza_standard' (nume) si 'score'.
    Returneaza [] daca LLM nu e disponibil sau apelul esueaza.
    """
    if not denumire_raw or len(denumire_raw.strip()) < 3:
        return []

    if not suggest_alias_llm_configured():
        return []

    ctx = ""
    if categorie_pdf and str(categorie_pdf).strip():
        ctx = f"Secțiune / categorie în buletin (PDF): «{str(categorie_pdf).strip()}».\n"

    prompt = (
        "Ești un parser medical pentru analize de laborator (România). "
        "Primești o denumire extrasă din buletin (posibil OCR imperfect). "
        "Returnezi o listă scurtă de denumiri canonice de analize de laborator în română "
        "(cum ar apărea în catalogul unui laborator: Hemoglobină, Glicemie, TGO/AST, etc.).\n"
        + ctx
        + "Răspunde DOAR cu JSON valid, format: "
        '{"candidates": [{"name": "Hemoglobina", "score": 95}, ...]}\n'
        f"Denumire din buletin: «{denumire_raw.strip()}»\n"
    )
    if snippets:
        prompt += "Context valori lângă analiză în buletin: " + ", ".join(snippets[:5]) + "\n"

    try:
        text = chat_completion_system_user(
            "You are a helpful medical lab parser assistant. Respond only with valid JSON.",
            prompt,
            max_tokens=350,
            temperature=0.0,
        )
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return []

        parsed = json.loads(text[start : end + 1])
        candidates = parsed.get("candidates") or parsed.get("suggestions") or []
        if not isinstance(candidates, list):
            return []

        result = []
        for item in candidates[:5]:
            if not isinstance(item, dict):
                continue
            name = (item.get("name") or item.get("label") or item.get("candidate") or "").strip()
            if not name:
                continue
            result.append(
                {
                    "analiza_standard": name,
                    "score": float(item.get("score") or 0),
                }
            )
        return result

    except Exception as exc:
        _log.warning("LLM suggestion failed for '%s': %s", denumire_raw, exc)
        return []


def map_llm_candidates_to_analiza_standard(
    llm_rows: List[Dict[str, Any]],
    analize_standard: List[dict],
    *,
    fuzzy_cutoff: int = 72,
) -> List[Dict[str, Any]]:
    """
    Potrivește numele returnate de LLM la rânduri din `analiza_standard` (fuzzy pe denumire_standard).
    Returnează listă cu chei: analiza_standard_id, denumire_standard, cod_standard, llm_score, fuzzy_score, combined_score.
    """
    if not llm_rows or not analize_standard:
        return []

    choices = [(s.get("denumire_standard") or "").strip() for s in analize_standard]
    out: List[Dict[str, Any]] = []
    seen_ids: set[int] = set()

    for row in llm_rows:
        name_llm = (row.get("analiza_standard") or "").strip()
        if not name_llm:
            continue
        llm_sc = float(row.get("score") or 0)
        best = process.extractOne(
            name_llm,
            choices,
            scorer=fuzz.WRatio,
            score_cutoff=fuzzy_cutoff,
        )
        if not best:
            continue
        match_name, fuzzy_sc, idx = best[0], best[1], best[2]
        std = analize_standard[idx]
        aid = std.get("id")
        if aid is None:
            continue
        try:
            aid_int = int(aid)
        except (TypeError, ValueError):
            continue
        if aid_int in seen_ids:
            continue
        # combină încrederea LLM (0–100) cu potrivirea fuzzy
        combined = round((llm_sc * 0.45 + fuzzy_sc * 0.55) if llm_sc > 0 else fuzzy_sc, 1)
        out.append(
            {
                "analiza_standard_id": aid_int,
                "denumire_standard": std.get("denumire_standard"),
                "cod_standard": std.get("cod_standard"),
                "llm_name": name_llm,
                "llm_score": round(llm_sc, 1),
                "fuzzy_score": round(float(fuzzy_sc), 1),
                "combined_score": combined,
            }
        )
        seen_ids.add(aid_int)
        if len(out) >= 5:
            break

    out.sort(key=lambda x: (-x["combined_score"], -x.get("fuzzy_score", 0)))
    return out


def sugestii_necunoscuta_cu_catalog(
    denumire_raw: str,
    analize_standard: List[dict],
    *,
    categorie_pdf: Optional[str] = None,
    snippets: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Un singur rând necunoscut: LLM + mapare la catalog. Lista goală dacă LLM indisponibil."""
    raw = suggest_alias_from_llm(denumire_raw, snippets=snippets, categorie_pdf=categorie_pdf)
    return map_llm_candidates_to_analiza_standard(raw, analize_standard)
