# -*- coding: utf-8 -*-
"""Completare analize din încărcarea anterioară (aceeași dată buletin, același pacient)."""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from backend.config import settings
from backend.database import get_prior_buletin_id_same_date, get_rezultate_buletin
from backend.models import PatientParsed, RezultatParsat

_log = logging.getLogger(__name__)


def _sid_set_from_parsed(rezultate: list) -> set[int]:
    out: set[int] = set()
    for r in rezultate:
        sid = getattr(r, "analiza_standard_id", None)
        if sid is None:
            continue
        try:
            out.add(int(sid))
        except (TypeError, ValueError):
            continue
    return out


def _row_has_value(row: dict) -> bool:
    if row.get("valoare") is not None:
        return True
    vt = row.get("valoare_text")
    return bool(vt and str(vt).strip())


def _parsat_value_missing(r: RezultatParsat) -> bool:
    if r.valoare is not None:
        return False
    vt = (r.valoare_text or "").strip()
    return not vt


def _prior_map_first_with_value(prior_rows: list) -> dict[int, dict]:
    """Prima apariție per analiza_standard_id care are valoare (pentru copiere)."""
    out: dict[int, dict] = {}
    for row in prior_rows:
        sid = row.get("analiza_standard_id")
        if sid is None:
            continue
        try:
            si = int(sid)
        except (TypeError, ValueError):
            continue
        if si in out:
            continue
        if _row_has_value(row):
            out[si] = row
    return out


def apply_gap_fill_from_prior_upload(
    parsed: PatientParsed,
    *,
    pacient_id: int,
    new_buletin_id: int,
    data_buletin_iso: Optional[str],
    laborator: Optional[str],
) -> Tuple[int, int, str]:
    """
    1) Completează valori lipsă pe rânduri deja parsate (același analiza_standard_id ca în buletinul anterior).
    2) Adaugă rânduri noi pentru analize mapate care lipsesc complet din parsare.

    Returnează (număr rânduri noi, număr valori completate pe rând existent, mesaj pentru UI sau gol).
    """
    if not getattr(settings, "prior_upload_gap_fill_enabled", True):
        return (0, 0, "")
    target = (data_buletin_iso or "").strip()
    if len(target) < 10:
        return (0, 0, "")

    prior_id = get_prior_buletin_id_same_date(
        pacient_id,
        new_buletin_id,
        target,
        laborator,
    )
    if prior_id is None:
        return (0, 0, "")

    prior_rows = get_rezultate_buletin(int(prior_id))
    if not prior_rows:
        return (0, 0, "")

    prior_by_sid = _prior_map_first_with_value(prior_rows)
    if not prior_by_sid:
        return (0, 0, "")

    value_fills = 0
    for r in list(parsed.rezultate or []):
        if not isinstance(r, RezultatParsat):
            continue
        if not _parsat_value_missing(r):
            continue
        sid = r.analiza_standard_id
        if sid is None:
            continue
        try:
            si = int(sid)
        except (TypeError, ValueError):
            continue
        prow = prior_by_sid.get(si)
        if not prow or not _row_has_value(prow):
            continue

        r.valoare = prow.get("valoare")
        r.valoare_text = prow.get("valoare_text")
        if r.flag is None and prow.get("flag"):
            r.flag = prow.get("flag")
        if r.interval_min is None and prow.get("interval_min") is not None:
            r.interval_min = prow.get("interval_min")
        if r.interval_max is None and prow.get("interval_max") is not None:
            r.interval_max = prow.get("interval_max")
        if not (r.unitate or "").strip() and (prow.get("unitate") or "").strip():
            r.unitate = prow.get("unitate")

        r.needs_review = True
        rr = list(r.review_reasons or [])
        if "completare_valoare_din_incarcare_anterioara" not in rr:
            rr.append("completare_valoare_din_incarcare_anterioara")
        r.review_reasons = rr
        r.gap_fill_source_buletin_id = int(prior_id)
        value_fills += 1

    present = _sid_set_from_parsed(list(parsed.rezultate or []))
    added = 0
    used_sids: set[int] = set()

    for row in prior_rows:
        sid = row.get("analiza_standard_id")
        if sid is None:
            continue
        try:
            si = int(sid)
        except (TypeError, ValueError):
            continue
        if si in present or si in used_sids:
            continue
        if not _row_has_value(row):
            continue

        new_r = RezultatParsat(
            analiza_standard_id=si,
            denumire_raw=row.get("denumire_raw"),
            valoare=row.get("valoare"),
            valoare_text=row.get("valoare_text"),
            unitate=row.get("unitate"),
            interval_min=row.get("interval_min"),
            interval_max=row.get("interval_max"),
            flag=row.get("flag"),
            categorie=row.get("categorie"),
            ordine=row.get("ordine"),
            needs_review=True,
            review_reasons=["completare_din_incarcare_anterioara"],
            gap_fill_source_buletin_id=int(prior_id),
        )
        parsed.rezultate.append(new_r)
        present.add(si)
        used_sids.add(si)
        added += 1

    if added or value_fills:
        _log.info(
            "gap_fill: buletin %s — valori=%s randuri_noi=%s din buletin %s",
            new_buletin_id,
            value_fills,
            added,
            prior_id,
        )
        parts = []
        if value_fills:
            parts.append(f"{value_fills} valori completate pe rânduri existente")
        if added:
            parts.append(f"{added} analize adăugate (lipseau din parsare)")
        msg = (
            "Din încărcarea anterioară (buletin #%s, aceeași dată): %s."
            % (prior_id, ", ".join(parts))
        )
        return (added, value_fills, msg)
    return (0, 0, "")
