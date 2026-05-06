"""Analizeaza PDF-urile Laza 22.12.2025: extrage text, parseaza, compara cu DB.
Identifica diferentele intre upload-uri si ce trebuie imbunatatit in parser/normalizer.
"""
import os
import sys

# DATABASE_URL inainte de orice import backend (config.py il verifica)
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

PDF1 = r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\3a221403-54a0-4cdc-bf7c-a9878caf83e7\buletin analize 22.12.2025 ....pdf"
PDF2 = r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\58b59afb-a62e-48a0-a717-47fb324bf9b7\buletin analize 22.12.2025.pdf"

def main():
    from backend.pdf_processor import extract_text_from_pdf
    from backend.parser import parse_full_text
    from backend.normalizer import normalize_rezultate
    import psycopg2
    import psycopg2.extras

    DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway")

    print("=" * 70)
    print("ANALIZA PDF-URI LAZA 22.12.2025 - Comparatie si verificare")
    print("=" * 70)

    # 1. Extrage text din ambele PDF-uri
    for label, path in [("PDF1 (....pdf)", PDF1), ("PDF2 (.pdf)", PDF2)]:
        if not os.path.exists(path):
            print(f"\n[SKIP] {label}: fisierul nu exista: {path}")
            continue
        print(f"\n--- {label} ---")
        try:
            text, tip, err, _ = extract_text_from_pdf(path)
            print(f"Tip: {tip}, Eroare OCR: {err or '-'}")
            print(f"Lungime text: {len(text)} caractere")
            # Primele 1500 caractere pentru preview
            preview = text[:1500].replace("\n", " | ")
            print(f"Preview: {preview[:500]}...")
        except Exception as e:
            print(f"Eroare extragere: {e}")

    # 2. Parseaza ambele PDF-uri
    rez_parse = {}
    for label, path in [("PDF1", PDF1), ("PDF2", PDF2)]:
        if not os.path.exists(path):
            continue
        try:
            text, _, _, _ = extract_text_from_pdf(path)
            parsed = parse_full_text(text)
            if parsed:
                rez_parse[label] = parsed
                print(f"\n--- Parsat {label}: CNP={parsed.cnp}, Nume={parsed.nume}")
                print(f"   Rezultate extrase: {len(parsed.rezultate)}")
                for i, r in enumerate(parsed.rezultate[:15]):
                    v = r.valoare if r.valoare is not None else (r.valoare_text or "-")
                    print(f"   [{i+1}] {r.denumire_raw[:45]:45} -> {v}")
                if len(parsed.rezultate) > 15:
                    print(f"   ... +{len(parsed.rezultate)-15} mai multe")
            else:
                print(f"\n--- Parsat {label}: FAIL (CNP negasit)")
        except Exception as e:
            print(f"\n--- Parsat {label}: EROARE {e}")
            import traceback
            traceback.print_exc()

    # 3. Normalizare (mapare la analiza_standard)
    rez_norm = {}
    for label, parsed in rez_parse.items():
        if not parsed:
            continue
        try:
            norm = normalizare_rezultate(parsed.rezultate)
            rez_norm[label] = norm
            nemapate = [r for r in norm if r.analiza_standard_id is None]
            mapate = [r for r in norm if r.analiza_standard_id is not None]
            print(f"\n--- Normalizat {label}: {len(mapate)} mapate, {len(nemapate)} nemapate")
            if nemapate:
                for r in nemapate[:10]:
                    print(f"   NEMAPAT: '{r.denumire_raw}'")
        except Exception as e:
            print(f"\n--- Normalizat {label}: EROARE {e}")

    # 4. Date din DB pentru Laza (buletine 22.12)
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT p.id, p.cnp, p.nume, p.prenume FROM pacienti p
        WHERE p.nume ILIKE '%Laza%' OR p.prenume ILIKE '%Laza%'
    """)
    pacienti = cur.fetchall()
    print("\n" + "=" * 70)
    print("PACIENTI LAZA IN DB")
    print("=" * 70)
    for p in pacienti:
        print(f"  id={p['id']} cnp={p['cnp']} nume={p['nume']} prenume={p['prenume']}")

    cur.execute("""
        SELECT b.id, b.data_buletin, b.fisier_original
        FROM buletine b
        JOIN pacienti p ON p.id = b.pacient_id
        WHERE (p.nume ILIKE '%Laza%' OR p.prenume ILIKE '%Laza%')
        ORDER BY b.id
    """)
    buletine = cur.fetchall()
    print(f"\nBuletine Laza: {len(buletine)}")
    for b in buletine:
        print(f"  id={b['id']} data={b['data_buletin']} fisier={b['fisier_original']}")

    # Rezultate din buletinele 22.12 (presupunem ca 45, 46 sunt cele 2 fisiere 22.12)
    for bid in [b["id"] for b in buletine]:
        cur.execute("""
            SELECT r.denumire_raw, r.valoare, r.valoare_text, r.unitate, a.denumire_standard
            FROM rezultate_analize r
            LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
            WHERE r.buletin_id = %s
            ORDER BY r.ordine NULLS LAST, r.id
        """, (bid,))
        rows = cur.fetchall()
        print(f"\n--- Buletin {bid} - {len(rows)} rezultate ---")
        for i, r in enumerate(rows[:20]):
            v = r["valoare"] if r["valoare"] is not None else (r["valoare_text"] or "-")
            std = r["denumire_standard"] or "NEMAPAT"
            print(f"  [{i+1}] {r['denumire_raw'][:40]:40} -> {v} | {std}")
        if len(rows) > 20:
            print(f"  ... +{len(rows)-20}")

    # 5. Comparatie: ce difera intre PDF1 si PDF2 (daca ambele exista)
    if "PDF1" in rez_parse and "PDF2" in rez_parse:
        p1 = {r.denumire_raw: (r.valoare, r.valoare_text) for r in rez_parse["PDF1"].rezultate}
        p2 = {r.denumire_raw: (r.valoare, r.valoare_text) for r in rez_parse["PDF2"].rezultate}
        only1 = set(p1) - set(p2)
        only2 = set(p2) - set(p1)
        diff_val = []
        for k in set(p1) & set(p2):
            if p1[k] != p2[k]:
                diff_val.append((k, p1[k], p2[k]))
        print("\n" + "=" * 70)
        print("DIFERENTE INTRE PDF1 SI PDF2 (parsare)")
        print("=" * 70)
        print(f"  Doar in PDF1: {len(only1)} - {list(only1)[:5]}")
        print(f"  Doar in PDF2: {len(only2)} - {list(only2)[:5]}")
        print(f"  Aceeasi denumire, valoare diferita: {len(diff_val)}")
        for k, v1, v2 in diff_val[:5]:
            print(f"    '{k[:40]}': {v1} vs {v2}")

    conn.close()
    print("\n[DONE]")

if __name__ == "__main__":
    main()
