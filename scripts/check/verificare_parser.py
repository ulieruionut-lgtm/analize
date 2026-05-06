# -*- coding: utf-8 -*-
"""
Verificare REALA: ce text extrage pdfplumber si ce produce parserul.
Ruleaza: python verificare_parser.py
(necesita: pip install pdfplumber pydantic pydantic-settings)
"""
import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PDF_PATH = r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\1c519765-1585-4cfd-96c0-93bed9dae410\buletin analize 13.02.2026.pdf"

def main():
    if not os.path.exists(PDF_PATH):
        print("PDF nu exista la calea data. Verifica path-ul.")
        return

    # 1. Extragere text cu pdfplumber (cum face aplicatia)
    print("=== 1. TEXT EXTRAS CU pdfplumber (cum face aplicatia) ===\n")
    try:
        import pdfplumber
        text_plumber = ""
        with pdfplumber.open(PDF_PATH) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_plumber += t + "\n"
        text_plumber = text_plumber.strip()
        print("Lungime:", len(text_plumber), "caractere")
        print("\nPrimele 2000 caractere:")
        print(text_plumber[:2000])
        print("\n... [trunchiat] ...\n")
    except Exception as e:
        print("EROARE pdfplumber:", e)
        text_plumber = ""

    # 2. Extragere cu fitz (PyMuPDF) - fallback OCR
    print("\n=== 2. TEXT EXTRAS CU fitz (PyMuPDF) ===\n")
    try:
        import fitz
        text_fitz = ""
        doc = fitz.open(PDF_PATH)
        for page in doc:
            text_fitz += page.get_text() + "\n"
        doc.close()
        text_fitz = text_fitz.strip()
        print("Lungime:", len(text_fitz), "caractere")
    except Exception as e:
        print("EROARE fitz:", e)
        text_fitz = ""

    # 3. Parser pe ambele texte + COMBINAT (strategia noua)
    print("\n=== 3. REZULTATE PARSER ===\n")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from backend.parser import extract_rezultate, parse_full_text
        from backend.pdf_processor import extract_text_from_pdf

        for nume, text in [("pdfplumber", text_plumber), ("fitz", text_fitz)]:
            if not text:
                continue
            print(f"--- Cu text din {nume} ---")
            try:
                rez = extract_rezultate(text)
                print(f"Nr analize: {len(rez)}")
                for r in rez[:30]:
                    v = r.valoare if r.valoare is not None else r.valoare_text
                    print(f"  {r.denumire_raw} = {v} {r.unitate or ''}")
                if len(rez) > 30:
                    print(f"  ... +{len(rez)-30} mai multe")
            except Exception as ex:
                print("EROARE:", ex)
            print()

        # Extragere COMBINATA (pymupdf + pdfplumber) - strategia din pdf_processor
        print("--- Cu extract_text_from_pdf (COMBINAT) ---")
        try:
            text_comb, tip, err, colored, extractor = extract_text_from_pdf(PDF_PATH)
            print(f"Extractor: {extractor}, tip: {tip}, lungime: {len(text_comb)}")
            if text_comb:
                rez = extract_rezultate(text_comb)
                print(f"Nr analize: {len(rez)}")
                for r in rez[:30]:
                    v = r.valoare if r.valoare is not None else r.valoare_text
                    print(f"  {r.denumire_raw} = {v} {r.unitate or ''}")
                if len(rez) > 30:
                    print(f"  ... +{len(rez)-30} mai multe")
        except Exception as ex:
            print("EROARE:", ex)
        print()

        # Full parse pe text combinat
        if text_plumber or text_fitz:
            text_comb = (text_fitz or "") + "\n" + (text_plumber or "")
            text_comb = text_comb.strip()
            p = parse_full_text(text_comb)
            if p:
                print(f"COMBINAT -> CNP: {p.cnp}, Nume: {p.nume} {p.prenume}")
                print(f"TOTAL analize: {len(p.rezultate)}")
            else:
                print("parse_full_text a returnat None")
    except ImportError as e:
        print("Import error (verifica venv):", e)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
