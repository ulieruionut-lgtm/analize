import psycopg2, os
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
# Cauta toate randurile suspecte (scurte, fara cod standard, sau cu denumire ciudata)
cur.execute("""
    SELECT r.id, r.buletin_id, r.denumire_raw, r.valoare, r.unitate, r.analiza_standard_id
    FROM rezultate_analize r
    WHERE r.analiza_standard_id IS NULL
       OR length(r.denumire_raw) < 6
       OR r.denumire_raw ILIKE '%certificat%'
       OR r.denumire_raw ILIKE 'eGFR%'
       OR r.denumire_raw ~ '^[: ][a-z ]'
    ORDER BY r.buletin_id, r.id
""")
rows = cur.fetchall()
print(f"Total randuri suspecte: {len(rows)}\n")
for r in rows:
    print(f"  id={r[0]} buletin={r[1]} | '{r[2]}' = {r[3]} {r[4] or ''} | cod_std={r[5]}")
conn.close()
