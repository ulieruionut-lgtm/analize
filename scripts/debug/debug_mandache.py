"""Compara datele Mandache din DB cu PDF-ul."""
import os, sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding="utf-8")
DB = os.environ.get("DATABASE_URL", "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway")
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT p.id, p.cnp, p.nume, p.prenume FROM pacienti p
    WHERE LOWER(p.nume) LIKE '%mandache%'
""")
rows = cur.fetchall()
print("Pacienti Mandache:", rows)

for p in rows:
    cur.execute("""
        SELECT b.id, b.data_buletin, b.fisier_original FROM buletine b
        WHERE b.pacient_id = %s ORDER BY b.id DESC
    """, (p["id"],))
    buletine = cur.fetchall()
    print(f"\n{p['nume']} {p['prenume']}: {len(buletine)} buletine")
    for b in buletine:
        cur.execute("""
            SELECT r.denumire_raw, r.valoare, r.valoare_text, r.unitate, a.denumire_standard
            FROM rezultate_analize r
            LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
            WHERE r.buletin_id = %s
            ORDER BY COALESCE(r.ordine,999), r.id
        """, (b["id"],))
        rez = cur.fetchall()
        print(f"  Buletin {b['id']} ({b['fisier_original']}): {len(rez)} rezultate")
        for z in rez:
            v = z.get("valoare") if z.get("valoare") is not None else z.get("valoare_text")
            print(f"    {str(z['denumire_raw'])[:50]:50} -> {v} {z['unitate'] or '':10} | {z['denumire_standard'] or '-'}")

conn.close()
