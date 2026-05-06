# -*- coding: utf-8 -*-
"""
Procesează mai multe PDF-uri, colectează analize necunoscute și gunoi, salvează pentru corectare.
"""
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    for p in [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]:
        if os.path.isfile(p):
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = p
            except Exception:
                pass
            os.environ["PATH"] = os.path.dirname(p) + os.pathsep + os.environ.get("PATH", "")
            break

from backend.pdf_processor import extract_text_from_pdf
from backend.parser import parse_full_text
from backend.normalizer import normalize_rezultate

PDFS = [
    r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\546ef3c2-f696-4605-bc9d-5050015dfb29\buletin analize 19.02.2026.pdf",
    r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\e3807d92-e82e-4541-8ece-99de9f0e79b5\buletin analize 06.11.2025.pdf",
    r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\969cccc0-44e0-4a07-b263-27008348708c\buletin analize 07.11.2025.pdf",
    r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\cfa85d8b-bf51-4d21-a926-972ab94ae56c\buletin analieze 22.12.2025.pdf",
    r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\e8febe50-23d5-42de-a166-450e28e32b33\buletin analieze 22.12.2025....pdf",
]

def proceseaza(pdf_path):
    path = Path(pdf_path)
    if not path.exists():
        return None, None, f"Nu există: {path}"
    text, tip, err, _, extractor = extract_text_from_pdf(str(path))
    if len(text) < 80:
        return None, None, f"Text insuficient ({len(text)} chars)"
    parsed = parse_full_text(text, cnp_optional=True)
    if not parsed or not parsed.rezultate:
        return None, None, "Fără analize extrase"
    rez = normalize_rezultate(parsed.rezultate)
    nec = [(r.denumire_raw, r.valoare, r.unitate) for r in rez if r.analiza_standard_id is None and r.denumire_raw]
    rec = [(r.denumire_raw, r.analiza_standard_id) for r in rez if r.analiza_standard_id is not None]
    return rec, nec, None

if __name__ == "__main__":
    toate_nec = {}
    for pdf in PDFS:
        name = Path(pdf).name
        print(f"\n--- {name} ---")
        rec, nec, err = proceseaza(pdf)
        if err:
            print(f"  {err}")
            continue
        print(f"  Recunoscute: {len(rec)} | Necunoscute: {len(nec)}")
        for raw, val, um in nec:
            k = raw.strip() if raw else ""
            if k:
                toate_nec[k] = toate_nec.get(k, 0) + 1

    print("\n=== TOATE NECUNOSCUTE (agregat) ===")
    for raw, cnt in sorted(toate_nec.items(), key=lambda x: -x[1]):
        print(f"  {cnt}x | {raw[:70]}")
