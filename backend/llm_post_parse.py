# -*- coding: utf-8 -*-
"""
După OCR + parser + normalizare: pentru rânduri fără analiza_standard_id,
folosește același lanț ca la „Sugestii AI” (LLM + fuzzy pe catalog) și, peste un prag,
salvează alias în DB (învățare pentru upload-uri ulterioare).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.database import get_all_analize_standard
from backend.llm_chat import suggest_alias_llm_configured
from backend.llm_helper import sugestii_necunoscuta_cu_catalog
from backend.models import RezultatParsat
from backend.normalizer import adauga_alias_nou

_log = logging.getLogger(__name__)


def _categorie_pentru_denumire(lista: List[RezultatParsat], den: str) -> Optional[str]:
    den = (den or "").strip()
    for r in lista:
        if (r.denumire_raw or "").strip() == den:
            c = (getattr(r, "categorie", None) or "").strip()
            return c or None
    return None


def apply_llm_learn_after_normalize(
    lista: List[RezultatParsat],
    laborator_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Pentru fiecare denumire_raw unică încă nemapată, apelează sugestii (Haiku + catalog).
    Dacă cea mai bună sugestie are combined_score >= prag, salvează alias și setează
    analiza_standard_id pe toate rândurile din listă cu aceeași denumire.

    Nu rulează dacă feature-ul e oprit sau lipsesc chei LLM.
    """
    out: Dict[str, Any] = {
        "enabled": bool(getattr(settings, "llm_learn_from_upload_enabled", False)),
        "ran": False,
        "auto_applied": 0,
        "llm_calls": 0,
        "skipped_reason": None,
        "details": [],
        "warnings": [],
    }

    if not out["enabled"]:
        out["skipped_reason"] = "disabled_in_config"
        return out

    if not suggest_alias_llm_configured():
        out["skipped_reason"] = "llm_not_configured"
        out["warnings"].append(
            "Învățare LLM: lipsește cheie API (ex. ANTHROPIC_API_KEY) sau LLM_PROVIDER."
        )
        return out

    min_score = float(getattr(settings, "llm_learn_auto_apply_min_score", 86.0) or 86.0)
    max_calls = max(1, int(getattr(settings, "llm_learn_max_calls_per_upload", 40) or 40))

    from backend.parser import este_denumire_gunoi

    # Denumiri unice nemapate
    seen_raw: set[str] = set()
    unice: List[str] = []
    for r in lista:
        if r.analiza_standard_id is not None:
            continue
        raw = (r.denumire_raw or "").strip()
        # NOTE: Accept short names too (min 1 char for codes like K, Na, pH, Ca, Fe, etc.)
        # Old check: if len(raw) < 3: continue  ← THIS WAS BLOCKING SHORT ANALYSIS NAMES
        if len(raw) < 1:
            continue
        if este_denumire_gunoi(raw):
            continue
        if raw in seen_raw:
            continue
        seen_raw.add(raw)
        unice.append(raw)

    if not unice:
        out["ran"] = True
        out["skipped_reason"] = "nothing_to_map"
        return out

    std = get_all_analize_standard()
    if not std:
        out["warnings"].append("Catalog analize standard gol — învățare LLM oprită.")
        return out

    n_unice = len(unice)
    unice = unice[:max_calls]
    if n_unice > max_calls:
        out["warnings"].append(
            f"Învățare LLM: limitat la {max_calls} denumiri distincte pe buletin ({n_unice} găsite)."
        )

    out["ran"] = True
    applied_keys: set[str] = set()

    for den in unice:
        try:
            # Emit LLM call event
            try:
                from backend.learning_events import emit_learning_event
                emit_learning_event("llm_call", den, laborator_id=laborator_id)
            except Exception:
                pass
            
            cat_pdf = _categorie_pentru_denumire(lista, den)
            sug = sugestii_necunoscuta_cu_catalog(
                den, std, categorie_pdf=cat_pdf, snippets=None
            )
        except Exception as exc:
            # Emit error event
            try:
                from backend.learning_events import emit_learning_event
                emit_learning_event("error", den, error=str(exc)[:100], laborator_id=laborator_id)
            except Exception:
                pass
            
            _log.warning("llm_learn failed for %r: %s", den[:80], exc)
            out["details"].append(
                {
                    "denumire_raw": den[:200],
                    "error": str(exc)[:200],
                    "applied": False,
                }
            )
            continue
        out["llm_calls"] += 1

        if not sug:
            out["details"].append(
                {
                    "denumire_raw": den[:200],
                    "applied": False,
                    "reason": "no_suggestion",
                }
            )
            continue

        best = sug[0]
        sc = float(best.get("combined_score") or 0.0)
        aid = best.get("analiza_standard_id")
        if aid is None or sc < min_score:
            out["details"].append(
                {
                    "denumire_raw": den[:200],
                    "applied": False,
                    "best_score": sc,
                    "best_label": best.get("denumire_standard"),
                    "reason": "below_threshold" if sc < min_score else "no_id",
                }
            )
            continue

        try:
            aid_int = int(aid)
        except (TypeError, ValueError):
            continue

        key = den.strip()
        if key in applied_keys:
            continue

        ok = adauga_alias_nou(den, aid_int)
        applied_keys.add(key)
        out["auto_applied"] += 1
        
        # Emit learning success event
        try:
            from backend.learning_events import emit_learning_event
            emit_learning_event(
                "alias_learned",
                den,
                mapped_to=best.get("denumire_standard"),
                score=sc,
                laborator_id=laborator_id,
                details={"analiza_standard_id": aid_int}
            )
        except Exception:
            pass

        for r in lista:
            if (r.denumire_raw or "").strip() == key and r.analiza_standard_id is None:
                r.analiza_standard_id = aid_int
                # Nu mai e necunoscut pentru markerii de review
                if getattr(r, "review_reasons", None) and "alias_necunoscut" in r.review_reasons:
                    try:
                        r.review_reasons = [x for x in r.review_reasons if x != "alias_necunoscut"]
                    except Exception:
                        pass
                    if not r.review_reasons:
                        r.needs_review = False

        out["details"].append(
            {
                "denumire_raw": den[:200],
                "applied": True,
                "alias_salvat": ok,
                "analiza_standard_id": aid_int,
                "denumire_standard": best.get("denumire_standard"),
                "combined_score": sc,
                "sursa": best.get("sursa"),
            }
        )

    return out
