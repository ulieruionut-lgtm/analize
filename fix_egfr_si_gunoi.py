"""
Adauga eGFR ca analiza standard, mapeaza 'eGFR =' si sterge gunoi din toate buletinele.
"""
import psycopg2, os
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

print("=== Fix eGFR + curatare gunoi ===\n")

# 1. Adauga eGFR ca analiza standard daca nu exista
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='EGFR'")
row = cur.fetchone()
if row:
    egfr_id = row[0]
    print(f"eGFR deja exista cu id={egfr_id}")
else:
    cur.execute("""
        INSERT INTO analiza_standard (cod_standard, denumire_standard, unitate_implicita, interval_min, interval_max)
        VALUES ('EGFR', 'Rata de filtrare glomerulara estimata (eGFR)', 'ml/min/1.73m²', 60, 120)
        RETURNING id
    """)
    egfr_id = cur.fetchone()[0]
    print(f"eGFR adaugat cu id={egfr_id}")

# 2. Adauga alias-uri pentru eGFR
aliases_egfr = [
    'eGFR =', 'eGFR=', 'eGFR', 'EGFR', 'Rata de filtrare glomerulara',
    'Rata filtrare glomerulara estimata', 'RFGe', 'GFR',
    'eGFR (CKD-EPI)', 'eGFR CKD-EPI',
]
for alias in aliases_egfr:
    cur.execute("""
        INSERT INTO analiza_alias (analiza_standard_id, alias)
        VALUES (%s, %s) ON CONFLICT DO NOTHING
    """, (egfr_id, alias))
print(f"Alias-uri eGFR adaugate: {len(aliases_egfr)}")

# 3. Mapeaza 'eGFR =' din toate buletinele
cur.execute("""
    UPDATE rezultate_analize
    SET analiza_standard_id=%s
    WHERE denumire_raw ILIKE 'eGFR%%'
      AND denumire_raw NOT ILIKE 'eGFR:%%'
      AND analiza_standard_id IS NULL
""", (egfr_id,))
print(f"eGFR mapat in {cur.rowcount} randuri")

# 4. Sterge gunoiul din TOATE buletinele (nu doar 12)
cur.execute("""
    DELETE FROM rezultate_analize
    WHERE denumire_raw IN (': s i', 'E e', ': s I', ': s i', 'E e', 'i Ea a acte o oa a', 'k =', 'o A', 'PD')
       OR denumire_raw ILIKE '%%CERTIFICAT%%'
       OR (denumire_raw ILIKE 'eGFR:%%' AND valoare BETWEEN 1 AND 200)
""")
print(f"Randuri gunoi sterse din toate buletinele: {cur.rowcount}")

conn.commit()
conn.close()
print("\n=== Gata! ===")
