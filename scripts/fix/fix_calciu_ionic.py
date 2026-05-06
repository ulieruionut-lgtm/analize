import psycopg2, psycopg2.extras, sys
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)

conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1. Adauga analiza standard Calciu ionic (daca nu exista)
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'CALCIU_IONIC'")
row = cur.fetchone()
if row:
    calciu_ionic_id = row['id']
    print(f"Calciu ionic exista deja cu ID={calciu_ionic_id}")
else:
    cur.execute(
        "INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES ('CALCIU_IONIC', 'Calciu ionic (Ca2+)') RETURNING id"
    )
    calciu_ionic_id = cur.fetchone()['id']
    print(f"ADAUGAT analiza standard: 'Calciu ionic (Ca2+)' cu ID={calciu_ionic_id}")

# 2. Adauga/actualizeaza aliasurile
aliasuri_de_mapat = ["CALCIU IONIC", "Calciu ionic", "Ca ionic", "Ca2+", "Calciu ionizat"]
for alias in aliasuri_de_mapat:
    cur.execute("SELECT id, analiza_standard_id FROM analiza_alias WHERE LOWER(alias) = LOWER(%s)", (alias,))
    existing = cur.fetchone()
    if existing:
        if existing['analiza_standard_id'] != calciu_ionic_id:
            cur.execute("UPDATE analiza_alias SET analiza_standard_id = %s WHERE id = %s", (calciu_ionic_id, existing['id']))
            print(f"  ACTUALIZAT alias: '{alias}' -> Calciu ionic")
        else:
            print(f"  OK deja: '{alias}'")
    else:
        cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s, %s)", (alias, calciu_ionic_id))
        print(f"  ADAUGAT alias: '{alias}'")

# 3. Remapeaza rezultatele gresit mapate
cur.execute("""
    SELECT r.id, r.denumire_raw, a.denumire_standard, r.valoare
    FROM rezultate_analize r
    JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE LOWER(r.denumire_raw) LIKE '%%calciu ion%%'
    AND r.analiza_standard_id != %s
""", (calciu_ionic_id,))
gresit = cur.fetchall()
print(f"\nRezultate gresit mapate: {len(gresit)}")
for r in gresit:
    print(f"  RID={r['id']} raw='{r['denumire_raw']}' val={r['valoare']} era -> '{r['denumire_standard']}'")

if gresit:
    cur.execute("""
        UPDATE rezultate_analize SET analiza_standard_id = %s
        WHERE LOWER(denumire_raw) LIKE '%%calciu ion%%'
        AND analiza_standard_id != %s
    """, (calciu_ionic_id, calciu_ionic_id))
    print(f"  => Remapate la 'Calciu ionic (Ca2+)'")

conn.commit()

# Verifica final
cur.execute("SELECT alias FROM analiza_alias WHERE analiza_standard_id = %s", (calciu_ionic_id,))
aliasuri = [r['alias'] for r in cur.fetchall()]
print(f"\nStare finala: ID={calciu_ionic_id} | aliasuri={aliasuri}")
print("Gata!")
conn.close()
