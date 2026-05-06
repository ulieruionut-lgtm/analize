# -*- coding: utf-8 -*-
"""
Pas 1: Investigare completa - ce buletine au ce gunoi si care sunt fisierele PDF.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import psycopg2, psycopg2.extras
DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Toate buletinele cu nr analize nemapate
cur.execute("""
    SELECT b.id, b.fisier_original, b.created_at,
           p.cnp, p.nume, p.prenume,
           COUNT(ra.id) as total,
           SUM(CASE WHEN ra.analiza_standard_id IS NULL THEN 1 ELSE 0 END) as nec
    FROM buletine b
    JOIN pacienti p ON b.pacient_id = p.id
    LEFT JOIN rezultate_analize ra ON ra.buletin_id = b.id
    GROUP BY b.id, b.fisier_original, b.created_at, p.cnp, p.nume, p.prenume
    ORDER BY b.id
""")
buletine = cur.fetchall()
print("=== TOATE BULETINELE ===")
for b in buletine:
    print(f"  B{b['id']} {b['cnp']} {b['nume']} {b['prenume'] or ''} | {(b['fisier_original'] or '?')[:50]} | {b['total']} tot, {b['nec']} nec")

# Detalii gunoi pentru fiecare buletin cu probleme
for b in buletine:
    if not b['nec']:
        continue
    print(f"\n--- B{b['id']} {b['nume']} {b['prenume'] or ''} ({b['nec']} NEMAPATE) ---")
    cur.execute("""
        SELECT id, denumire_raw, valoare, unitate
        FROM rezultate_analize
        WHERE buletin_id = %s AND analiza_standard_id IS NULL
        ORDER BY id
    """, (b['id'],))
    for r in cur.fetchall():
        print(f"  id={r['id']} val={r['valoare']} | {(r['denumire_raw'] or '')[:80]}")

conn.close()
