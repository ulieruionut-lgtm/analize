# -*- coding: utf-8 -*-
"""Rulează extragerea pe buletinul Vladasel din PDF și afișează rezultatele pentru comparație."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PDF = Path(
    r"c:\Users\Ionut\AppData\Roaming\Cursor\User\workspaceStorage"
    r"\a9286e2cac6d7b0788d913c4d6803a14\pdfs\36ffc6fc-2f43-461f-9c36-d5553487bda9"
    r"\buletin analize 22.12.2025 ....pdf"
)


def main() -> None:
    from backend.pdf_processor import extract_text_from_pdf
    from backend.parser import parse_full_text
    from backend.lab_detect import resolve_laborator_id_for_text
    from backend.normalizer import normalize_rezultate

    if not PDF.is_file():
        print("Lipsește PDF:", PDF)
        return

    out = text, tip, ocr_err, colored, extractor = extract_text_from_pdf(str(PDF))
    print("=== EXTRACȚIE PDF ===")
    print("tip:", tip, "extractor:", extractor, "len_text:", len(text or ""))
    if ocr_err:
        print("ocr_err:", ocr_err[:500])

    parsed = parse_full_text(text or "", cnp_optional=True)
    if not parsed:
        print("parse_full_text -> None")
        return

    lab_id, _ = resolve_laborator_id_for_text(text, PDF.name)
    normalize_rezultate(parsed.rezultate, laborator_id=lab_id)

    print("pacient:", parsed.nume, parsed.prenume, "cnp:", parsed.cnp)
    print("=== ANALIZE (aplicație)", len(parsed.rezultate), ") ===")
    for i, r in enumerate(parsed.rezultate, 1):
        cat = (getattr(r, "categorie", None) or "")[:18]
        vt = (r.valoare_text or "")[:80]
        print(
            f"{i:3}. [{cat:<18}] {r.denumire_raw!r} "
            f"v={r.valoare!r} u={r.unitate!r} imin={r.interval_min!r} imax={r.interval_max!r} "
            f"vt={vt!r}"
        )


if __name__ == "__main__":
    main()
