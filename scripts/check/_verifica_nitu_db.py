# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os, psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.environ.get("DATABASE_URL", "")
if not DB_URL:
    # incearca din .env
    env_file = os.path.join(os.path.dirname(__file__), "backend", ".env")
    if os.path.exists(env_file):
        for line in open(env_file):
            if line.startswith("DATABASE_URL"):
                DB_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if not DB_URL:
    print("DATABASE_URL nu gasit!")
    sys.exit(1)

conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=RealDictCursor)

# Gasim pacientul Nitu
cur.execute("SELECT id, cnp, nume, prenume FROM pacienti WHERE cnp = '5240222080031' OR LOWER(nume) LIKE '%nitu%'")
pacienti = cur.fetchall()
print("Pacienti gasiti:")
for p in pacienti:
    print(f"  id={p['id']} cnp={p['cnp']} {p['nume']} {p['prenume']}")

if not pacienti:
    print("Pacient nu gasit!")
    conn.close()
    sys.exit(1)

pac_id = pacienti[0]['id']

# Buletine
cur.execute("SELECT id, data_recoltare, fisier_sursa FROM buletine WHERE pacient_id = %s ORDER BY data_recoltare DESC", (pac_id,))
buletine = cur.fetchall()
print(f"\nBuletine ({len(buletine)}):")
for b in buletine:
    print(f"  buletin id={b['id']} data={b['data_recoltare']} fisier={b['fisier_sursa']}")

# Rezultate pentru fiecare buletin
for b in buletine:
    cur.execute("""
        SELECT ra.id, ra.denumire_raw, ra.valoare, ra.unitate, 
               COALESCE(ans.cod_standard, '?') as cod, COALESCE(ans.denumire, '?') as denumire_std
        FROM rezultate_analize ra
        LEFT JOIN analiza_standard ans ON ans.id = ra.analiza_standard_id
        WHERE ra.buletin_id = %s
        ORDER BY ra.id
    """, (b['id'],))
    rezultate = cur.fetchall()
    print(f"\n  Buletin {b['id']} ({b['data_recoltare']}) - {len(rezultate)} rezultate:")
    for r in rezultate:
        mapped = f"[{r['cod']}]" if r['cod'] != '?' else "[NEMAPAT]"
        print(f"    {mapped} {r['denumire_raw']} = {r['valoare']} {r['unitate']}")

conn.close()
