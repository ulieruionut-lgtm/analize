# -*- coding: utf-8 -*-
"""AI Copilot: audit LLM opțional la upload — verificare încrucișată parser vs extragere API."""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from backend.config import settings
from backend.llm_chat import audit_llm_has_credentials, chat_completion_system_user, resolve_model_name

_log = logging.getLogger(__name__)

# Limită prudentă pentru context (caractere), sub pragul tipic de tokeni
_MAX_TEXT_CHARS = 48000


def copilot_audit_enabled() -> bool:
    if not bool(getattr(settings, "llm_buletin_audit_enabled", False)):
        return False
    return audit_llm_has_credentials()


def _truncate_buletin_text(text: str) -> str:
    t = (text or "").strip()
    if len(t) <= _MAX_TEXT_CHARS:
        return t
    head = _MAX_TEXT_CHARS // 2
    tail = _MAX_TEXT_CHARS - head - 100
    return t[:head] + "\n\n[... TEXT TRUNCHIAT PENTRU CONTEXT ...]\n\n" + t[-tail:]


def _strip_diacritics(s: str) -> str:
    if not s:
        return ""
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c))


def _norm_name(s: str) -> str:
    x = _strip_diacritics((s or "").lower())
    x = re.sub(r"\s+", " ", x).strip()
    return x


def _parse_val_cell(v: Any, val_text: Optional[str]) -> Tuple[Optional[float], str]:
    if v is not None and isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v), str(v)
    s = (str(v) if v is not None else "") or (val_text or "")
    s = s.strip().replace(",", ".")
    s = re.sub(r"^([<>]=?)\s*", "", s)
    m = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", s)
    if m:
        try:
            return float(m.group(0)), m.group(0)
        except ValueError:
            pass
    return None, _norm_name(s)


def _vals_close(a: Optional[float], b: Optional[float], sa: str, sb: str) -> bool:
    if a is not None and b is not None:
        tol = max(0.02, 0.015 * max(abs(a), abs(b), 1.0))
        return abs(a - b) <= tol
    return _norm_name(sa) == _norm_name(sb) and bool(_norm_name(sa))


def _names_similar(a: str, b: str) -> bool:
    na, nb = _norm_name(a), _norm_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # Substring: scurt ≥ 3 și lung începe cu scurtul (ex: "VSH" ⊂ "VSH -Sange - Metoda Westergreen")
    short, long_ = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(short) >= 3 and (long_.startswith(short + " ") or long_.startswith(short + "-")):
        return True
    if len(na) >= 4 and len(nb) >= 4 and (na in nb or nb in na):
        return True
    return SequenceMatcher(None, na, nb).ratio() >= 0.82


def _call_llm_for_analize(truncated_text: str) -> Tuple[List[Dict[str, Any]], Optional[int], str]:
    system = (
        "Ești un extractor medical. Primești textul unui buletin de analize de laborator. "
        "Extrage TOATE liniile care sunt rezultate de analiză (denumire + valoare numerică sau text, unitate dacă există). "
        "Ignoră anteturi, date personale, note generice fără valoare. "
        "Răspunde DOAR cu JSON valid, fără markdown. Schema (valoare = număr sau șir):\n"
        '{"analize":[{"denumire":"string","valoare":"<număr sau text>","unitate":"string sau gol"}],"total_analize":<număr>}\n'
        "total_analize trebuie să fie egal cu lungimea listei analize."
    )
    user = (
        "Analizează buletinul și extrage toate analizele cu valori. La final numărul total în total_analize.\n\n"
        "--- BULETIN (text) ---\n"
        + truncated_text
    )
    raw = chat_completion_system_user(
        system,
        user,
        max_tokens=8000,
        temperature=0.0,
    )
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```\s*$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Răspuns LLM fără JSON obiect.")
    data = json.loads(raw[start : end + 1])
    rows = data.get("analize") or data.get("rows") or data.get("results") or []
    if not isinstance(rows, list):
        rows = []
    total = data.get("total_analize")
    if total is not None:
        try:
            total = int(total)
        except (TypeError, ValueError):
            total = None
    cleaned: List[Dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        den = (item.get("denumire") or item.get("name") or item.get("test") or "").strip()
        if not den:
            continue
        val = item.get("valoare")
        if val is None:
            val = item.get("value")
        unit = item.get("unitate") if item.get("unitate") is not None else item.get("unit")
        unit_s = (str(unit).strip() if unit is not None else "") or None
        cleaned.append({"denumire": den, "valoare": val, "unitate": unit_s})
    return cleaned, total, raw[:2000]


def _cross_check(
    app_rows: List[Dict[str, Any]], llm_rows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Potrivire în două treceri: nume+valoare, apoi doar nume (conflict valoare)."""
    n_app = len(app_rows)
    n_llm = len(llm_rows)
    referinta = max(n_app, n_llm, 1)

    used_app: set[int] = set()
    used_llm: set[int] = set()
    value_mismatch: List[Dict[str, Any]] = []

    # LLM → APP: întâi potriviri cu aceeași valoare (sau echivalent)
    llm_idx = list(range(n_llm))
    app_idx = list(range(n_app))
    for li in llm_idx:
        if li in used_llm:
            continue
        lr = llm_rows[li]
        lname = lr.get("denumire") or ""
        lf, ls = _parse_val_cell(lr.get("valoare"), None)
        best_aj: Optional[int] = None
        best_score = 0.0
        for aj in app_idx:
            if aj in used_app:
                continue
            ar = app_rows[aj]
            aname = ar.get("denumire") or ""
            af, aas = _parse_val_cell(ar.get("valoare"), ar.get("valoare_text"))
            if not _names_similar(lname, aname):
                continue
            name_r = SequenceMatcher(None, _norm_name(lname), _norm_name(aname)).ratio()
            val_ok = _vals_close(lf, af, ls, aas)
            if not val_ok:
                continue
            score = name_r + 0.2
            if score > best_score:
                best_score = score
                best_aj = aj
        if best_aj is not None and best_score >= 0.82:
            used_app.add(best_aj)
            used_llm.add(li)

    matched_both = len(used_llm)  # după prima trecere: nume + valoare

    # A doua trecere: același nume, valoare diferită
    for li in llm_idx:
        if li in used_llm:
            continue
        lr = llm_rows[li]
        lname = lr.get("denumire") or ""
        lf, ls = _parse_val_cell(lr.get("valoare"), None)
        best_aj: Optional[int] = None
        best_score = 0.0
        for aj in app_idx:
            if aj in used_app:
                continue
            ar = app_rows[aj]
            aname = ar.get("denumire") or ""
            af, aas = _parse_val_cell(ar.get("valoare"), ar.get("valoare_text"))
            if not _names_similar(lname, aname):
                continue
            if _vals_close(lf, af, ls, aas):
                continue
            name_r = SequenceMatcher(None, _norm_name(lname), _norm_name(aname)).ratio()
            if name_r > best_score:
                best_score = name_r
                best_aj = aj
        if best_aj is not None and best_score >= 0.85:
            used_app.add(best_aj)
            used_llm.add(li)
            ar = app_rows[best_aj]
            value_mismatch.append(
                {
                    "app_denumire": ar.get("denumire"),
                    "llm_denumire": lr.get("denumire"),
                    "app_valoare": ar.get("valoare"),
                    "llm_valoare": lr.get("valoare"),
                }
            )

    only_app = [app_rows[j] for j in range(n_app) if j not in used_app]
    only_llm = [llm_rows[j] for j in range(n_llm) if j not in used_llm]

    # Procente: referință = max(liste) — „cât din referință acoperă aplicația cu acord nume+valoare”
    pct_aplicatie_recunoastere = round(100.0 * matched_both / referinta, 1)
    # „Ajutor AI”: cât din referință e vizibil doar la LLM sau în conflict (semnal de verificat)
    gap = len(only_llm) + len(only_app) + len(value_mismatch)
    pct_semne_ai_verificare = round(100.0 * gap / referinta, 1)
    union_denom = max(1, n_app + n_llm - matched_both)
    pct_acord_pe_union = round(100.0 * matched_both / union_denom, 1)

    def _lim(lst: List[Any], n: int = 25) -> List[Any]:
        return lst[:n] if len(lst) > n else lst

    return {
        "count_app": n_app,
        "count_llm": n_llm,
        "reference": referinta,
        "matched_nume_si_valoare": matched_both,
        "only_app": _lim(only_app),
        "only_llm": _lim(only_llm),
        "value_mismatch": _lim(value_mismatch, 20),
        "pct_aplicatie_vs_referinta": min(100.0, pct_aplicatie_recunoastere),
        "pct_discrepanta_vs_referinta": min(100.0, pct_semne_ai_verificare),
        "pct_acord_pe_union": min(100.0, pct_acord_pe_union),
    }


def run_copilot_audit(text: str, app_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Rulează auditul (apel rețea). Apelatorul trebuie să verifice copilot_audit_enabled() înainte.
    Returnează mereu un dict cu status ok|error.
    """
    try:
        truncated = _truncate_buletin_text(text)
        if len(truncated) < 40:
            return {
                "status": "skipped",
                "message": "Text prea scurt pentru audit AI Copilot.",
                "cross_check": None,
            }
        llm_rows, total_decl, _raw_snip = _call_llm_for_analize(truncated)
        cross = _cross_check(app_rows, llm_rows)
        cross["llm_total_declared"] = total_decl
        if total_decl is not None and total_decl != len(llm_rows):
            cross["note_total"] = f"LLM a declarat total_analize={total_decl}, dar lista are {len(llm_rows)} rânduri."
        return {
            "status": "ok",
            "model": resolve_model_name(),
            "llm_rows": len(llm_rows),
            "cross_check": cross,
        }
    except Exception as ex:
        _log.warning("AI Copilot audit failed: %s", ex)
        return {
            "status": "error",
            "message": str(ex)[:400],
            "cross_check": None,
        }


def maybe_run_copilot_audit(text: str, app_rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Dacă feature-ul e oprit, returnează None (nu include cheie în răspuns). Altfel dict audit."""
    if not copilot_audit_enabled():
        return None
    return run_copilot_audit(text, app_rows)


def apply_audit_corrections_to_db(
    audit_result: Dict[str, Any],
    buletin_id: int,
) -> Dict[str, Any]:
    """
    Aplică corecții din auditul LLM în DB:
    - value_mismatch: marchează rândul cu needs_review=True + reason "llm_value_mismatch"
    - only_llm: adaugă denumirea în analiza_necunoscuta pentru review admin

    Nu modifică valorile — flag informativ. Sigur de rulat chiar dacă audit e parțial.
    """
    out: Dict[str, Any] = {"nr_mismatch_marked": 0, "nr_only_llm_added": 0, "erori": []}
    try:
        cross = (audit_result.get("cross_check") or {})
        mismatches: List[Dict[str, Any]] = cross.get("value_mismatch") or []
        only_llm: List[Dict[str, Any]] = cross.get("only_llm") or []
    except Exception as e:
        out["erori"].append(f"parse audit_result: {e}")
        return out

    # --- value_mismatch → needs_review pe rândul din DB ---
    if mismatches:
        try:
            from backend.database import get_rezultat_id_by_buletin_and_raw, mark_rezultat_needs_review
        except ImportError as e:
            out["erori"].append(f"import db: {e}")
            mismatches = []
    for item in mismatches:
        den = (item.get("app_denumire") or item.get("denumire") or "").strip()
        if not den:
            continue
        try:
            rez_id = get_rezultat_id_by_buletin_and_raw(buletin_id, den)
            if rez_id is not None:
                mark_rezultat_needs_review(rez_id, "llm_value_mismatch")
                out["nr_mismatch_marked"] += 1
        except Exception as e:
            out["erori"].append(f"mismatch mark {den!r}: {e}")

    # --- only_llm → log în analiza_necunoscuta ---
    if only_llm:
        try:
            from backend.normalizer import _log_necunoscuta
        except ImportError as e:
            out["erori"].append(f"import normalizer: {e}")
            only_llm = []
    for item in only_llm:
        den = (item.get("denumire") or item.get("app_denumire") or "").strip()
        if not den:
            continue
        try:
            _log_necunoscuta(den, categorie_buletin=None, laborator_id=None)
            out["nr_only_llm_added"] += 1
        except Exception as e:
            out["erori"].append(f"log necunoscuta {den!r}: {e}")

    return out
