"""Verifica datele Laza din DB - fara PDF."""
import os
import sys
import psycopg2
import psycopg2.extras

sys.stdout.reconfigure(encoding="utf-8")
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway",
)

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT p.id, p.cnp, p.nume, p.prenume
        FROM pacienti p WHERE p.nume ILIKE '%Laza%'
    """)
    pacienti = cur.fetchall()
    print("=== Pacienti Laza ===\n")
    for p in pacienti:
        print(f"id={p['id']} cnp={p['cnp']} nume={repr(p['nume'])} prenume={repr(p['prenume'])}")

    for p in pacienti:
        cur.execute("""
            SELECT b.id, b.data_buletin, b.fisier_original, b.created_at
            FROM buletine b WHERE b.pacient_id = %s ORDER BY b.id
        """, (p["id"],))
        buletine = cur.fetchall()
        print(f"\n=== Buletine pacient {p['id']} ({p['nume']}) ===\n")
        for b in buletine:
            data_str = b["data_buletin"].strftime("%d.%m.%Y") if b["data_buletin"] else "?"
            print(f"  Buletin id={b['id']} data={data_str} fisier={b['fisier_original']}")

        for b in buletine:
            cur.execute("""
                SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate,
                       r.interval_min, r.interval_max, r.flag, r.analiza_standard_id,
                       a.denumire_standard, a.cod_standard
                FROM rezultate_analize r
                LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
                WHERE r.buletin_id = %s
                ORDER BY COALESCE(r.ordine, 99999), r.id
            """, (b["id"],))
            rows = cur.fetchall()
            data_str = b["data_buletin"].strftime("%d.%m.%Y") if b["data_buletin"] else "?"
            print(f"\n--- Rezultate Buletin {b['id']} ({data_str}) - {len(rows)} analize ---")
            for r in rows:
                std = r["denumire_standard"] or "?"
                raw = (r["denumire_raw"] or "")[:50]
                v = r["valoare"] if r["valoare"] is not None else (r["valoare_text"] or "-")
                print(f"  {std} | raw={raw} | val={v} {r['unitate'] or ''}")

    conn.close()

if __name__ == "__main__":
    main()
