# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import psycopg2, psycopg2.extras
DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1. Analize necunoscute
print("=== ANALIZE NECUNOSCUTE (toate) ===")
cur.execute("SELECT denumire_raw, aparitii, aprobata, analiza_standard_id FROM analiza_necunoscuta ORDER BY aprobata, aparitii DESC")
nec = cur.fetchall()
print(f"Total: {len(nec)}")
for r in nec:
    aprobata = "DA" if r['aprobata'] else "NU"
    raw = (r['denumire_raw'] or '')[:70]
    print(f"  [{r['aparitii']}x] aprobata={aprobata} | {raw}")

# 2. Rezultate fara analiza_standard_id
print("\n=== REZULTATE FARA MAPARE (analiza_standard_id=NULL) ===")
cur.execute("""
    SELECT ra.denumire_raw, COUNT(*) as n, p.nume
    FROM rezultate_analize ra
    JOIN buletine b ON ra.buletin_id = b.id
    JOIN pacienti p ON b.pacient_id = p.id
    WHERE ra.analiza_standard_id IS NULL
    GROUP BY ra.denumire_raw, p.nume
    ORDER BY n DESC
    LIMIT 30
""")
fara = cur.fetchall()
print(f"Total grupuri: {len(fara)}")
for r in fara:
    raw = (r['denumire_raw'] or '')[:70]
    print(f"  [{r['n']}x] {raw} ({r['nume']})")

# 3. Ultimele 5 buletine
print("\n=== ULTIMELE 5 BULETINE ===")
cur.execute("""
    SELECT b.id, p.nume, p.prenume, b.fisier_original, b.created_at,
           COUNT(ra.id) as total,
           SUM(CASE WHEN ra.analiza_standard_id IS NULL THEN 1 ELSE 0 END) as nec
    FROM buletine b
    JOIN pacienti p ON b.pacient_id = p.id
    LEFT JOIN rezultate_analize ra ON ra.buletin_id = b.id
    GROUP BY b.id, p.nume, p.prenume, b.fisier_original, b.created_at
    ORDER BY b.id DESC
    LIMIT 5
""")
for r in cur.fetchall():
    print(f"  B{r['id']} {r['nume']} {r['prenume'] or ''} | {(r['fisier_original'] or '?')[:40]} | {r['total']} analize, {r['nec']} necunoscute")

conn.close()
