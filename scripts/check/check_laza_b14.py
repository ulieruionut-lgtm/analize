# -*- coding: utf-8 -*-
import psycopg2, os
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Buletin 14 = Laza 05.12.2025
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.unitate, a.cod_standard
    FROM rezultate_analize r
    LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE r.buletin_id = 14
    ORDER BY a.denumire_standard NULLS LAST, r.id
""")
rows = cur.fetchall()
print(f"Buletin 14 (Laza 05.12.2025) - Total: {len(rows)} analize\n")
for r in rows:
    cod = r[4] or "??? NEMAPAT"
    print(f"  id={r[0]} | {r[2]} {r[3] or '':<10} [{cod}] | {r[1]}")

conn.close()
