import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)

conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

BULETIN_ID = 32

# ── 1. STERGE GUNOI ────────────────────────────────────────────────────────────
gunoi_rids = [
    987,   # '3) SRR E'
    988,   # 'Albumina %, i E PA E 57.68'  – duplicat corupt
    989,   # '_Globuline alfa 2%, DI i N'  – duplicat corupt
    993,   # 'Nume sii lancu Gheorghe Varsta: 83 ani,'
    1000,  # 'd lee cu iati...'
    1007,  # 'Paisie: CE TOME TRE'
    1012,  # '"Granulociteimature %*,' val=2020.0 – valoare imposibila
    1013,  # 'ni olt Tea'
    1014,  # 'Monocite. i iii -- INN Yu'
]
print("1. STERG GUNOI:")
for rid in gunoi_rids:
    cur.execute("SELECT denumire_raw FROM rezultate_analize WHERE id = %s", (rid,))
    row = cur.fetchone()
    if row:
        cur.execute("DELETE FROM rezultate_analize WHERE id = %s", (rid,))
        print(f"   STERS RID={rid}: '{row['denumire_raw']}'")

# ── 2. MAPEAZA ANALIZE NEMAPATE ────────────────────────────────────────────────
print("\n2. MAPEZ ANALIZE NEMAPATE:")
mapari = [
    # (rid, analiza_standard_id, denumire_standard)
    (990,  285, "Densitate urinara"),          # 'PDENSITATE URINARA, OO'
    (991,  290, "Urobilinogen urina"),          # '_UROBILINOGEN,, E | E'
    (994,  130, "Creatinina urinara"),          # 'Creatinina urinara'
    (999,  None, "Colesterol total"),           # 'Colesterol seric total' - verific codul
    (1004, 38,  "ALAT (TGP)"),                 # 'TGP/ALT'
    (1008, 3,   "Hemoglobina"),                # 'Hemoglobina, Cu E' val=14.8
    (1009, 4,   "Hematocrit"),                 # 'HOT,' val=39.5
]

# Gaseste ID-ul pentru Colesterol total
cur.execute("SELECT id FROM analiza_standard WHERE LOWER(cod_standard) = 'colesterol_total'")
col_row = cur.fetchone()
if col_row:
    for i, (rid, std_id, std_name) in enumerate(mapari):
        if std_name == "Colesterol total":
            mapari[i] = (rid, col_row['id'], std_name)
            break

# Gaseste ID-ul pentru Hemoglobina si Hematocrit
cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard WHERE LOWER(denumire_standard) LIKE '%%hemoglobin%%' OR LOWER(cod_standard) IN ('hgb','hb','hemoglobina') ORDER BY id LIMIT 3")
hgb_rows = cur.fetchall()
print(f"   Hemoglobina in standard: {[(r['id'], r['denumire_standard']) for r in hgb_rows]}")

cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard WHERE LOWER(cod_standard) IN ('hct','ht','hematocrit') OR LOWER(denumire_standard) LIKE '%%hematocrit%%' ORDER BY id LIMIT 3")
hct_rows = cur.fetchall()
print(f"   Hematocrit in standard: {[(r['id'], r['denumire_standard']) for r in hct_rows]}")

for rid, std_id, std_name in mapari:
    if std_id is None:
        print(f"   SKIP RID={rid}: nu am gasit ID pentru {std_name}")
        continue
    cur.execute(
        "UPDATE rezultate_analize SET analiza_standard_id = %s WHERE id = %s AND buletin_id = %s",
        (std_id, rid, BULETIN_ID)
    )
    if cur.rowcount:
        print(f"   MATAT RID={rid} -> {std_name} (ID={std_id})")
    else:
        print(f"   SKIP RID={rid}: nu a fost gasit in B{BULETIN_ID}")

# ── 3. CORECTEAZA ELECTROFOREZA ────────────────────────────────────────────────
print("\n3. CORECTEZ ELECTROFOREZA:")
# RID=1018 are valoarea gresita (3.86 in loc de 10.79) si e Alfa 2 globulina
cur.execute(
    "UPDATE rezultate_analize SET valoare = 10.79, analiza_standard_id = 133 WHERE id = 1018",
)
print("   FIX RID=1018: Electroforeza Alfa 2 globulina -> valoare 10.79 (corectata din 3.86)")

# Adauga Beta globulina, Gama globulina si Raport A/G (lipseau)
analize_lipsuri = [
    (134, "Electroforeza – Beta globulina",  "Globuline beta %",  12.03, "%"),
    (136, "Electroforeza – Gama globulina",  "Globuline gama %",  15.63, "%"),
    (137, "Raport A/G (electroforeza)",      "Raport A/G",        1.36,  ""),
]
for std_id, std_name, raw_name, valoare, unitate in analize_lipsuri:
    cur.execute(
        "SELECT id FROM rezultate_analize WHERE buletin_id = %s AND analiza_standard_id = %s",
        (BULETIN_ID, std_id)
    )
    if cur.fetchone():
        print(f"   EXISTA deja: {std_name}")
    else:
        cur.execute(
            "INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, unitate) "
            "VALUES (%s, %s, %s, %s, %s)",
            (BULETIN_ID, std_id, raw_name, valoare, unitate)
        )
        print(f"   ADAUGAT: {std_name} = {valoare} {unitate}")

# ── 4. ADAUGA ALIASURI NOI ────────────────────────────────────────────────────
print("\n4. ADAUG ALIASURI NOI:")
aliasuri_noi = [
    ("Albumina %",              131),  # ELECTRO_ALB
    ("Albumina%",               131),
    ("Globuline alfa 1 %",      132),  # ELECTRO_ALFA1
    ("Globuline alfa 1%",       132),
    ("Globuline alfa 2 %",      133),  # ELECTRO_ALFA2
    ("Globuline alfa 2%",       133),
    ("Globuline beta %",        134),  # ELECTRO_BETA1
    ("Globuline beta%",         134),
    ("Globuline gama %",        136),  # ELECTRO_GAMA
    ("Globuline gama%",         136),
    ("Raport A/G",              137),  # ELECTRO_RAPORT
    ("TGP/ALT",                 38),   # ALAT
    ("ALT/TGP",                 38),
    ("Colesterol seric total",  None), # se seteaza mai jos
    ("Creatinina urinara",      130),
    ("Albumina urinara*",       129),  # MICROALBUMIN
    ("Albumina urinara",        129),
    ("Densitate urinara",       285),
    ("DENSITATE URINARA",       285),
    ("Urobilinogen urina",      290),
    ("UROBILINOGEN",            290),
    ("Proteine totale serice",  None), # verific
]

# Gaseste ID colesterol total
if col_row:
    for i, (alias, sid) in enumerate(aliasuri_noi):
        if alias == "Colesterol seric total":
            aliasuri_noi[i] = (alias, col_row['id'])

# Gaseste ID Proteine totale
cur.execute("SELECT id FROM analiza_standard WHERE LOWER(cod_standard) = 'prot_totale' OR LOWER(denumire_standard) LIKE '%%proteine totale%%'")
pt_row = cur.fetchone()
if pt_row:
    for i, (alias, sid) in enumerate(aliasuri_noi):
        if alias == "Proteine totale serice":
            aliasuri_noi[i] = (alias, pt_row['id'])

for alias, std_id in aliasuri_noi:
    if std_id is None:
        print(f"   SKIP alias '{alias}': ID necunoscut")
        continue
    cur.execute("SELECT id FROM analiza_alias WHERE LOWER(alias) = LOWER(%s)", (alias,))
    if cur.fetchone():
        print(f"   EXISTA: '{alias}'")
    else:
        cur.execute(
            "INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s, %s)",
            (alias, std_id)
        )
        print(f"   NOU alias: '{alias}' -> ID={std_id}")

conn.commit()
print("\n✓ Toate modificarile au fost salvate!")
conn.close()
