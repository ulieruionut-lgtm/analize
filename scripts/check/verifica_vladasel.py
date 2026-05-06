# -*- coding: utf-8 -*-
"""Verifica datele pacientului Vladasel si identifica ce trebuie invatat (alias/parser)."""
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
import psycopg2.extras

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway",
)


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Pacienti Vladasel
    cur.execute("""
        SELECT p.id, p.cnp, p.nume, p.prenume
        FROM pacienti p
        WHERE p.nume ILIKE '%%Vladasel%%' OR p.nume ILIKE '%%VLADASEL%%'
        ORDER BY p.nume
    """)
    pacienti = cur.fetchall()
    if not pacienti:
        print("Niciun pacient Vladasel gasit in DB.")
        conn.close()
        return

    print("=== PACIENTI VLADASEL ===\n")
    for p in pacienti:
        print(f"  id={p['id']} cnp={p['cnp']} nume='{p['nume']}' prenume='{p['prenume']}'")

    # Buletine si rezultate pentru fiecare Vladasel
    for p in pacienti:
        pid = p["id"]
        nume_complet = f"{p['nume'] or ''} {p['prenume'] or ''}".strip()
        print(f"\n=== BULETINE: {nume_complet} (pacient_id={pid}) ===\n")

        cur.execute("""
            SELECT b.id, b.data_buletin, b.fisier_original
            FROM buletine b
            WHERE b.pacient_id = %s
            ORDER BY b.data_buletin NULLS LAST, b.id
        """, (pid,))
        buletine = cur.fetchall()

        if not buletine:
            print("  Nicio buletin.")
            continue

        for b in buletine:
            bid = b["id"]
            cur.execute("""
                SELECT r.id, r.denumire_raw, r.analiza_standard_id,
                       r.valoare, r.valoare_text, r.unitate, r.categorie,
                       a.denumire_standard, a.cod_standard
                FROM rezultate_analize r
                LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
                WHERE r.buletin_id = %s
                ORDER BY COALESCE(r.ordine, 99999), r.id
            """, (bid,))
            rezultate = cur.fetchall()

            print(f"  Buletin {bid}: {b['data_buletin']} - {b['fisier_original']}")
            print(f"    Total analize: {len(rezultate)}")

            # Grupare pe categorie
            by_cat = {}
            for r in rezultate:
                cat = r.get("categorie") or "(fara categorie)"
                if cat not in by_cat:
                    by_cat[cat] = []
                by_cat[cat].append(r)

            for cat in sorted(by_cat.keys()):
                lista = by_cat[cat]
                print(f"\n    --- {cat} ({len(lista)}) ---")
                for r in lista[:15]:
                    v = r["valoare"] if r["valoare"] is not None else (r["valoare_text"] or "-")
                    std = r["denumire_standard"] or r["denumire_raw"]
                    mapat = "OK" if r["analiza_standard_id"] else "NEMAPAT"
                    print(f"      {std} = {v} {r['unitate'] or ''} [{mapat}] raw='{r['denumire_raw'][:50] if r['denumire_raw'] else ''}'")
                if len(lista) > 15:
                    print(f"      ... +{len(lista)-15} mai multe")

            # Analize nemapate (pentru invatare)
            nemapate = [r for r in rezultate if not r["analiza_standard_id"]]
            if nemapate:
                print(f"\n    *** NEMAPATE (de invatat): {len(nemapate)} ***")
                for r in nemapate[:20]:
                    print(f"      raw='{r['denumire_raw']}' val={r['valoare'] or r['valoare_text']}")

    # Denumiri raw unice din Vladasel care nu sunt mapate
    print("\n\n=== DENUMIRI RAW NEMAPATE (candidati alias) ===\n")
    cur.execute("""
        SELECT r.denumire_raw, COUNT(*) as cnt
        FROM rezultate_analize r
        JOIN buletine b ON b.id = r.buletin_id
        JOIN pacienti p ON p.id = b.pacient_id
        WHERE (p.nume ILIKE '%%Vladasel%%' OR p.nume ILIKE '%%VLADASEL%%')
          AND r.analiza_standard_id IS NULL
          AND r.denumire_raw IS NOT NULL
          AND TRIM(r.denumire_raw) != ''
        GROUP BY r.denumire_raw
        ORDER BY cnt DESC
    """)
    raw_necunoscute = cur.fetchall()
    for r in raw_necunoscute:
        print(f"  '{r['denumire_raw'][:70]}' ({r['cnt']} apariții)")

    conn.close()
    print("\n=== GATA ===")


if __name__ == "__main__":
    main()
