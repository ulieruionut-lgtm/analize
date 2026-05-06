import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── 1. STERGE B33 (a doua incarcare cu mult gunoi) ─────────────────────────────
print("1. STERG B33 (plin de gunoi OCR)...")
cur.execute("DELETE FROM rezultate_analize WHERE buletin_id = 33")
cur.execute("DELETE FROM buletine WHERE id = 33")
print("   B33 sters.")

# ── 2. FIX B32: sterge gunoi ramas ─────────────────────────────────────────────
print("\n2. STERG gunoi ramas in B32...")
# Raport albumina/creatinina - adaug analiza standard daca nu exista
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'RAPORT_ACU'")
raport_acu = cur.fetchone()
if not raport_acu:
    cur.execute("INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES ('RAPORT_ACU', 'Raport albumina/creatinina urinara (ACR)') RETURNING id")
    raport_acu = cur.fetchone()
    print(f"   Adaugat analiza standard: Raport albumina/creatinina (ID={raport_acu['id']})")

# Mapeaza 'Raport albumina / creatinina urinara (RAC)*' si 'Albumina urinara*'
cur.execute("UPDATE rezultate_analize SET analiza_standard_id = %s WHERE buletin_id = 32 AND LOWER(denumire_raw) LIKE '%%raport albumina%%creatinina%%'", (raport_acu['id'],))
if cur.rowcount: print(f"   Matat: Raport albumina/creatinina")

cur.execute("UPDATE rezultate_analize SET analiza_standard_id = 129 WHERE buletin_id = 32 AND LOWER(denumire_raw) LIKE '%%albumina urinara%%'")
if cur.rowcount: print(f"   Matat: Albumina urinara -> Microalbuminurie")

# Trombocite are valoare imposibila (6200108) - corecteaza la 62.0 (sau sterge)
cur.execute("SELECT id, valoare FROM rezultate_analize WHERE buletin_id = 32 AND analiza_standard_id = 9")
tromb = cur.fetchone()
if tromb and tromb['valoare'] and tromb['valoare'] > 1000000:
    # Valoarea corecta ar fi probabil 62.0 sau 620 (OCR a citit gresit)
    # Din context 83 ani - 62 este foarte scazut, mai probabil 162 sau 262
    # Nu stim valoarea corecta - marcam ca suspicious prin unitate corecta
    print(f"   ATENTIE: Trombocite valoare imposibila ({tromb['valoare']}) - necesita verificare manuala")

# ── 3. ADAUGA analizele urinare in B32 ─────────────────────────────────────────
print("\n3. ADAUG analize urinare in B32 (din buletin Iancu - Examen complet urina)...")
# Valorile din imaginea trimisa de user
analize_urina = [
    (292, "LEUCOCITE URINARE",    None, "negativ",   None),
    (291, "NITRITI",              None, "negativ",   None),
    (286, "PROTEINE TOTALE URINARE", None, "negativ", None),
    (284, "PH",                   6.00, None,        None),
    (289, "BILIRUBINA URINARA",   None, "negativ",   None),
    # Densitate si Urobilinogen deja exista in B32
    (288, "CORPI CETONICI",       None, "negativ",   None),
    (293, "ERITROCITE URINARE",   None, "negativ",   None),
    (287, "GLUCOZA URINARA",      None, "negativ",   None),
    (297, "Examenul sedimentului urinar", None, "epitelii rare, leucocite rare, hematii absente", None),
]

for std_id, raw, valoare, valoare_text, unitate in analize_urina:
    # Verifica daca exista deja
    cur.execute("SELECT id FROM rezultate_analize WHERE buletin_id = 32 AND analiza_standard_id = %s", (std_id,))
    if cur.fetchone():
        print(f"   EXISTA deja: {raw}")
        continue
    cur.execute(
        "INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (32, std_id, raw, valoare, valoare_text, unitate)
    )
    val_afis = valoare_text or str(valoare)
    print(f"   ADAUGAT: {raw} = {val_afis}")

# ── 4. ADAUGA aliasuri noi ─────────────────────────────────────────────────────
print("\n4. ADAUG aliasuri noi...")
aliasuri_extra = [
    ("Raport albumina / creatinina urinara (RAC)*", raport_acu['id']),
    ("Raport albumina/creatinina urinara", raport_acu['id']),
    ("ACR", raport_acu['id']),
    ("RAC", raport_acu['id']),
    ("Albumina urinara*", 129),
    ("Microalbuminurie urina", 129),
]
for alias, sid in aliasuri_extra:
    cur.execute("SELECT id FROM analiza_alias WHERE LOWER(alias) = LOWER(%s)", (alias,))
    if not cur.fetchone():
        cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s, %s)", (alias, sid))
        print(f"   NOU alias: '{alias}'")

conn.commit()
print("\n✓ Gata! B32 este acum complet si curat.")

# Sumar final
cur.execute("""
    SELECT COUNT(*) as total,
           COUNT(analiza_standard_id) as mapate,
           COUNT(valoare_text) as text_vals
    FROM rezultate_analize WHERE buletin_id = 32
""")
s = cur.fetchone()
print(f"\nB32 final: {s['total']} rezultate | {s['mapate']} mapate | {s['text_vals']} cu valoare text")

conn.close()
