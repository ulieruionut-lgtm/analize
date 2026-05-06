"""Simuleaza parsarea PDF Nitu pentru a vedea ce extrage."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from pathlib import Path

pdf_path = Path(r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\1c8f0da7-3c07-4cba-88ed-8b6c773b228a\buletin analize 13.02.2026.pdf")

try:
    import fitz  # PyMuPDF
    doc = fitz.open(str(pdf_path))
    text = ""
    for p in doc:
        text += p.get_text()
    doc.close()
    print("=== PARSE ===")
    from backend.parser import parse_full_text, extract_rezultate
    parsed = parse_full_text(text)
    if parsed:
        print("CNP:", parsed.cnp, "| Nume:", parsed.nume, parsed.prenume)
        print(f"Rezultate: {len(parsed.rezultate)}")
        for r in parsed.rezultate[:25]:
            v = r.valoare if r.valoare is not None else r.valoare_text
            print(f"  {r.denumire_raw[:50]:50} -> {v} {r.unitate or ''}")
    else:
        print("parse_full_text returned None")
except Exception as e:
    print("Eroare:", e)
    import traceback
    traceback.print_exc()
