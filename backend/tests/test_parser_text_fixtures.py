"""Fixture-uri text-only pentru parser — fără PDF în git. Vezi docs/AUDIT_RECUNOASTERE_ANALIZE_SCANATE.md."""
import json
from pathlib import Path

import pytest

FIX_DIR = Path(__file__).resolve().parent / "fixtures" / "parser_text"
_MANIFEST = json.loads((FIX_DIR / "manifest.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _MANIFEST["cases"], ids=lambda c: c.get("id", c.get("file", "?")))
def test_parser_text_fixture_manifest(case: dict) -> None:
    from backend.parser import extract_rezultate

    path = FIX_DIR / case["file"]
    text = path.read_text(encoding="utf-8")
    rs = extract_rezultate(text)
    assert len(rs) >= int(case["min_count"]), f"{case['id']}: got {len(rs)}, expected >= {case['min_count']}"
    blob = " ".join((r.denumire_raw or "").lower() for r in rs)
    for sub in case.get("must_substrings", []):
        assert sub.lower() in blob, f"{case['id']}: missing substring {sub!r}"


def test_audit_linii_text_smoke() -> None:
    from backend.parser import audit_linii_text

    text = (FIX_DIR / "medlife_like.txt").read_text(encoding="utf-8")
    a = audit_linii_text(text)
    assert a["total_linii_non_goale"] >= 5
    assert a["linii_excluse_administrativ"] >= 0
    assert a["rezultate_extractate"] >= 3
    assert a["linii_acceptate_ca_parametru"] >= a["rezultate_extractate"]
    sm = a.get("semnale_multi_buletin_laborator")
    assert isinstance(sm, dict)
    assert "cnp_distincte" in sm and "laboratoare_mentionate_tot_textul" in sm
    assert "mesaj_scurt" in sm


def test_audit_linii_text_multi_brand_signal() -> None:
    from backend.parser import audit_linii_text

    t = "Antet MedLife laborator\n" + "linie\n" * 25 + "Footer Bioclinica\nGlicemie 5.5 mmol/L 3.9-6.0"
    a = audit_linii_text(t)
    sm = a["semnale_multi_buletin_laborator"]
    assert sm["pdf_probabil_compus_multi_buletin"] is True
    assert len(sm["laboratoare_mentionate_tot_textul"]) >= 2


def test_este_gunoi_ocr_accepts_urinary_keywords() -> None:
    """După extinderea _CUVINTE_MEDICALE: linii sumar/sediment nu sunt marcate gunoi."""
    from backend.parser import _este_gunoi_ocr

    assert not _este_gunoi_ocr("Nitriți – Absenți")
    assert not _este_gunoi_ocr("Claritate – Clar")
    assert not _este_gunoi_ocr("Proteine urinare – Absente")
    assert not _este_gunoi_ocr("Flora bacteriană – Absentă")
