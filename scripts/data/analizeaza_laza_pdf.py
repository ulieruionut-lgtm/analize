"""Compara PDF-urile Laza cu datele din DB. Extrage text, parseaza, identifica diferente."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PDF1 = r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\3a221403-54a0-4cdc-bf7c-a9878caf83e7\buletin analize 22.12.2025 ....pdf"
PDF2 = r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\58b59afb-a62e-48a0-a717-47fb324bf9b7\buletin analize 22.12.2025.pdf"

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway",
)


def main():
    import psycopg2
    import psycopg2.extras
    from backend.pdf_processor import extract_text_from_pdf
    from backend.parser import parse_full_text

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 1. Date Laza din DB
    cur.execute("""
        SELECT p.id, p.cnp, p.nume, p.prenume FROM pacienti p
        WHERE p.nume ILIKE '%Laza%' OR p.prenume ILIKE '%Laza%'
    """)
    pacienti = cur.fetchall()
    print("=== Pacienti Laza in DB ===")
    for p in pacienti:
        print(f"  id={p['id']} cnp={p['cnp']} nume={p['nume']} prenume={p['prenume']}")

    cur.execute("""
        SELECT b.id, b.pacient_id, b.data_buletin, b.fisier_original
        FROM buletine b
        JOIN pacienti p ON p.id = b.pacient_id
        WHERE p.nume ILIKE '%Laza%' OR p.prenume ILIKE '%Laza%'
        ORDER BY b.data_buletin DESC NULLS LAST, b.id DESC
    """)
    buletine = cur.fetchall()
    print(f"\n=== Buletine Laza ({len(buletine)}) ===")
    for b in buletine:
        print(f"  id={b['id']} data={b['data_buletin']} fisier={b['fisier_original']}")

    # 2. Extrage text din PDF-uri
    for label, path in [("PDF1 (....)", PDF1), ("PDF2", PDF2)]:
        print(f"\n=== {label}: {path} ===")
        if not os.path.exists(path):
            print("  FISIER NU EXISTA")
            continue
        try:
            text, tip, err, _ = extract_text_from_pdf(path)
            print(f"  Tip: {tip}, len={len(text)}")
            if err:
                print(f"  OCR err: {err}")
            # Parseaza
            parsed = parse_full_text(text)
            if parsed:
                print(f"  CNP parsat: {parsed.cnp}, Nume: {parsed.nume} {parsed.prenume or ''}")
                print(f"  Rezultate extrase: {len(parsed.rezultate)}")
                for i, r in enumerate(parsed.rezultate[:15]):
                    v = r.valoare if r.valoare is not None else (r.valoare_text or "")
                    print(f"    {i+1}. {r.denumire_raw} = {v} {r.unitate or ''}")
                if len(parsed.rezultate) > 15:
                    print(f"    ... +{len(parsed.rezultate)-15} mai multe")
            else:
                print("  Nu s-a putut parsa (CNP invalid?)")
            # Primele 80 linii din text
            lines = text.split("\n")
            print("\n  Primele 40 linii text:")
            for i, ln in enumerate(lines[:40]):
                if ln.strip():
                    print(f"    {i}: {repr(ln[:100])}")
        except Exception as e:
            print(f"  EROARE: {e}")
            import traceback
            traceback.print_exc()

    conn.close()
    print("\n=== GATA ===")


if __name__ == "__main__":
    main()
