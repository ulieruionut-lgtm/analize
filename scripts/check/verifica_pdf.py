# -*- coding: utf-8 -*-
"""Verifică un PDF: extrage text, parsează, afișează rezultatele și analize necunoscute."""
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def main(pdf_path: str):
    from backend.pdf_processor import extract_text_from_pdf
    from backend.parser import parse_full_text
    from backend.normalizer import normalize_rezultate

    path = Path(pdf_path)
    if not path.exists():
        print(f"EROARE: Fișierul nu există: {pdf_path}")
        return

    print(f"=== Procesare: {path.name} ===\n")
    text, tip, err, colored, extractor = extract_text_from_pdf(str(path))
    if err:
        print(f"Avertisment: {err}")
    if len(text) < 50:
        print(f"Text prea scurt sau gol ({len(text)} caractere).")
        print("PDF-urile scanate necesită Tesseract OCR: winget install UB-Mannheim.TesseractOCR")
        if text.strip():
            print("\nPrimele 500 caractere extrase:")
            print(repr(text[:500]))
        return

    print(f"Tip: {tip} | Extractor: {extractor} | {len(text)} caractere\n")
    parsed = parse_full_text(text, cnp_optional=True)
    if not parsed:
        print("Parsare eșuată.")
        return

    print(f"CNP: {parsed.cnp}")
    print(f"Nume: {parsed.nume} {parsed.prenume or ''}\n")

    rez = parsed.rezultate or []
    rez_norm = normalize_rezultate(rez)

    necunoscute = [r for r in rez_norm if r.analiza_standard_id is None]
    recunoscute = [r for r in rez_norm if r.analiza_standard_id is not None]

    print(f"--- REZULTATE RECUNOSCUTE ({len(recunoscute)}) ---")
    for r in recunoscute[:20]:
        print(f"  {r.denumire_raw or '?'} = {r.valoare} {r.unitate or ''} [id={r.analiza_standard_id}]")
    if len(recunoscute) > 20:
        print(f"  ... +{len(recunoscute)-20} alte")

    print(f"\n--- ANALIZE NECUNOSCUTE ({len(necunoscute)}) ---")
    for r in necunoscute:
        print(f"  {r.denumire_raw or '?'} = {r.valoare} {r.unitate or ''}")
    if not necunoscute:
        print("  (niciuna)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Utilizare: python verifica_pdf.py <cale_pdf>")
        sys.exit(1)
    main(sys.argv[1])
