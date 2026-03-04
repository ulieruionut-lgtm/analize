# -*- coding: utf-8 -*-
import psycopg2, os
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Gaseste cel mai recent buletin Laza din 05.12.2025
cur.execute("""
    SELECT b.id, b.data_buletin, b.fisier_original
    FROM buletine b
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE p.cnp = '2780416131279'
    ORDER BY b.id DESC
""")
buletine = cur.fetchall()
print("Buletine Laza:")
for b in buletine:
    print(f"  id={b[0]} data={b[1]} fisier={b[2]}")

# Cel mai recent buletin din dec 05
buletin_id = buletine[0][0]
print(f"\nAnalize in buletin {buletin_id}:")
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.unitate, a.cod_standard
    FROM rezultate_analize r
    LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE r.buletin_id = %s
    ORDER BY r.id
""", (buletin_id,))
rows = cur.fetchall()
print(f"Total: {len(rows)} analize")
print("\nCauta HGB/Hemoglobina/MCH/MCHC/VSH/Limfocite:")
for r in rows:
    dn = str(r[1]).lower()
    if any(x in dn for x in ['hgb','hemoglob','mch','mchc','vsh','viteza','limfoc','lymph','lym']):
        print(f"  GASIT id={r[0]}: '{r[1]}' = {r[2]} {r[3]} [{r[4]}]")

print("\nToate analizele:")
for r in rows:
    print(f"  id={r[0]} | '{r[1]}' = {r[2]} {r[3]} [{r[4]}]")

conn.close()
