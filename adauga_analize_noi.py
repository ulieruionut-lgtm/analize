import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)

conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Verifica ce analize urinare/PH exista
cur.execute(
    "SELECT id, denumire_standard, cod_standard FROM analiza_standard "
    "WHERE LOWER(denumire_standard) LIKE '%%urin%%' "
    "   OR LOWER(cod_standard) LIKE '%%urin%%' "
    "   OR LOWER(denumire_standard) LIKE '%%ph%%' "
    "ORDER BY denumire_standard"
)
existente = cur.fetchall()
print(f"Analize urinare/PH existente ({len(existente)}):")
for a in existente:
    print(f"  ID={a['id']} | {a['denumire_standard']} | cod={a['cod_standard']}")

# Analize urinare de adaugat (sumar urinar complet)
analize_noi = [
    ("PH_URINAR",        "pH urinar"),
    ("DENSITATE_URINARA","Densitate urinara"),
    ("PROTEINE_URINA",   "Proteine urina"),
    ("GLUCOZA_URINA",    "Glucoza urina"),
    ("CORPI_CETONICI",   "Corpi cetonici urina"),
    ("BILIRUBINA_URINA", "Bilirubina urina"),
    ("UROBILINOGEN_URINA","Urobilinogen urina"),
    ("NITRIT_URINA",     "Nitriti urina"),
    ("LEUCOCITE_URINA",  "Leucocite urina"),
    ("HEMATII_URINA",    "Hematii urina (eritrocite)"),
    ("BACTERII_URINA",   "Bacterii urina"),
    ("CULOARE_URINA",    "Culoare urina"),
    ("ASPECT_URINA",     "Aspect urina"),
    ("SEDIMENT_URINA",   "Sediment urinar"),
    ("CILINDRI_URINA",   "Cilindri urina"),
    ("CRISTALE_URINA",   "Cristale urina"),
    ("CELULE_EPITELIALE","Celule epiteliale urina"),
]

print(f"\n--- Adaugare analize noi ---")
adaugate = 0
for cod, denumire in analize_noi:
    # Verifica daca exista deja (dupa cod sau denumire)
    cur.execute(
        "SELECT id FROM analiza_standard WHERE cod_standard = %s OR LOWER(denumire_standard) = LOWER(%s)",
        (cod, denumire)
    )
    if cur.fetchone():
        print(f"  EXISTA: {denumire}")
    else:
        cur.execute(
            "INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES (%s, %s) RETURNING id",
            (cod, denumire)
        )
        new_id = cur.fetchone()['id']
        print(f"  ADAUGAT: [{new_id}] {denumire} (cod: {cod})")
        adaugate += 1

conn.commit()
print(f"\nTotal adaugate: {adaugate} analize noi.")

# Adauga si aliasuri comune pentru PH urinar
print("\n--- Adaugare aliasuri PH urinar ---")
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'PH_URINAR'")
ph_row = cur.fetchone()
if ph_row:
    ph_id = ph_row['id']
    aliasuri_ph = [
        "PH urinar", "pH urinar", "PH", "ph urinar",
        "Reactie (pH)", "Reactie pH", "pH", "pH urina",
        "Reactie urinara", "pH Urinar"
    ]
    for alias in aliasuri_ph:
        cur.execute("SELECT id FROM analiza_alias WHERE LOWER(alias) = LOWER(%s)", (alias,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s, %s)",
                (alias, ph_id)
            )
            print(f"  alias adaugat: '{alias}'")
    conn.commit()
    print(f"  Aliasuri PH salvate (ID analiza={ph_id})")

conn.close()
print("\nGata! Analizele noi sunt disponibile in aplicatie.")
