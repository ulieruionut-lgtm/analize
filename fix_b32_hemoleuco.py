import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── 1. ADAUGA ANALIZE STANDARD CARE LIPSESC ────────────────────────────────────
print("1. Adaug analize standard lipsa...")

analize_noi_std = [
    ("PLCR",        "P-LCR – Trombocite mari (%)"),
    ("RDW_SD",      "RDW-SD – Distributie eritrocite (SD)"),
    ("GRAN_IMT_PCT","Granulocite imature (%)"),
    ("GRAN_IMT_NR", "Granulocite imature (numar absolut)"),
    ("ERITROBL_NR",  "Eritroblasti (numar absolut)"),
    ("ERITROBL_PCT", "Eritroblasti (%)"),
]

id_map = {}  # cod -> id
for cod, denumire in analize_noi_std:
    cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = %s", (cod,))
    row = cur.fetchone()
    if row:
        id_map[cod] = row['id']
        print(f"   EXISTA: {denumire} (ID={row['id']})")
    else:
        cur.execute(
            "INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES (%s, %s) RETURNING id",
            (cod, denumire)
        )
        new_id = cur.fetchone()['id']
        id_map[cod] = new_id
        print(f"   ADAUGAT: {denumire} (ID={new_id})")

# ── 2. CORECTEAZA SI ADAUGA HEMOLEUCOGRAMA IN B32 ────────────────────────────
print("\n2. Corectez si adaug hemoleucograma in B32...")

# Datele din PDF (imagine atasata)
# std_id, raw_name, valoare, unitate, flag
# IDs cunoscute: 1=WBC, 2=RBC, 3=HGB, 4=HCT, 5=MCV, 6=MCH, 7=MCHC
# 8=RDW-CV, 9=PLT, 10=MPV, 11=PDW, 12=PCT
# 13=NEUTROFILE_PCT, 14=NEUTROFILE_NR
# 15=LIMFOCITE_PCT, 16=LIMFOCITE_NR
# 17=MONOCITE_PCT, 18=MONOCITE_NR
# 19=EOZINOFILE_PCT, 20=EOZINOFILE_NR
# 21=BAZOFILE_PCT, 22=BAZOFILE_NR

hemoleuco = [
    (1,   "Numar leucocite",          5.60,  "mii/uL", None),
    (2,   "Numar eritrocite",         4.34,  "mil/uL", None),
    (3,   "Hemoglobina",              14.80, "g/dL",   None),
    (4,   "HCT",                      39.50, "%",      None),
    (5,   "VEM",                      91.00, "fL",     None),
    (6,   "MCH",                      34.10, "pg",     None),
    (7,   "MCHC",                     37.50, "g/dL",   "H"),  # evidentiat in imagine
    (8,   "RDW-CV*",                  12.20, "%",      None),
    (id_map.get("RDW_SD"), "RDW-SD*", 41.30, "fL",    None),
    (9,   "Numar trombocite",        262.00, "mii/uL", None),
    (10,  "MPV",                      10.40, "fL",     None),
    (id_map.get("PLCR"),  "P-LCR*",  28.40, "%",      None),
    (12,  "PCT*",                      0.27, "%",      None),
    (11,  "PDW*",                     12.20, "fL",     None),
    (13,  "Neutrofile %",             54.90, "%",      None),
    (15,  "Limfocite %",              37.70, "%",      None),
    (17,  "Monocite %",                6.80, "%",      None),
    (19,  "Eozinofile %",              0.40, "%",      None),
    (21,  "Bazofile %",                0.20, "%",      None),
    (id_map.get("GRAN_IMT_PCT"), "Granulocite imature % *", 0.20, "%", None),
    (14,  "Neutrofile #",              3.08, "mii/uL", None),
    (16,  "Limfocite #",              2.11,  "mii/uL", None),
    (18,  "Monocite #",               0.38,  "mii/uL", None),
    (20,  "Eozinofile #",             0.02,  "mii/uL", None),
    (22,  "Bazofile #",               0.01,  "mii/uL", None),
    (id_map.get("GRAN_IMT_NR"),  "Granulocite imature # *", 0.01, "mii/uL", None),
    (id_map.get("ERITROBL_NR"), "Eritroblasti # *",  0.00, "mii/uL", None),
    (id_map.get("ERITROBL_PCT"), "Eritroblasti % *", 0.00, "%",      None),
]

# Corecteaza RID=1008 (Hemoglobina cu unitate gresita "gd" -> "g/dL")
cur.execute("UPDATE rezultate_analize SET valoare=14.80, unitate='g/dL' WHERE id=1008")
print("   CORECTAT RID=1008: Hemoglobina 14.80 g/dL")

# Corecteaza RID=1010 (Trombocite cu unitate "ul" -> "mii/uL")
cur.execute("UPDATE rezultate_analize SET unitate='mii/uL' WHERE id=1010")
print("   CORECTAT RID=1010: Trombocite 262 mii/uL")

# Corecteaza RID=1011 (Bazofile % - exista deja, skip la adaugare)
cur.execute("SELECT analiza_standard_id FROM rezultate_analize WHERE id=1011")
baz = cur.fetchone()

for std_id, raw, val, unitate, flag in hemoleuco:
    if std_id is None:
        print(f"   SKIP (fara ID std): {raw}")
        continue

    # Verifica daca exista deja
    cur.execute(
        "SELECT id, valoare FROM rezultate_analize WHERE buletin_id=32 AND analiza_standard_id=%s",
        (std_id,)
    )
    existing = cur.fetchone()
    if existing:
        # Actualizeaza daca valoarea e incorecta
        if existing['valoare'] != val:
            cur.execute(
                "UPDATE rezultate_analize SET valoare=%s, unitate=%s, flag=%s WHERE id=%s",
                (val, unitate, flag, existing['id'])
            )
            print(f"   ACTUALIZAT RID={existing['id']}: {raw} = {val} {unitate}")
        else:
            print(f"   OK (exista): {raw} = {val} {unitate}")
    else:
        cur.execute(
            "INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, unitate, flag) "
            "VALUES (32, %s, %s, %s, %s, %s)",
            (std_id, raw, val, unitate, flag)
        )
        print(f"   ADAUGAT: {raw} = {val} {unitate}{' ['+flag+']' if flag else ''}")

# ── 3. ADAUGA ALIASURI ─────────────────────────────────────────────────────────
print("\n3. Adaug aliasuri hemoleuco...")
aliasuri = [
    ("Numar leucocite",     1), ("Numar leucocite.",   1),
    ("Numar eritrocite",    2), ("Numar eritrocite.",  2),
    ("Numar trombocite.",   9), ("Numar trombocite",   9),
    ("HCT",                 4), ("HCT .",              4),
    ("VEM",                 5), ("VEM .",              5),
    ("MCH",                 6), ("MCH .",              6),
    ("MCHC",                7), ("MCHC .",             7),
    ("RDW-CV*",             8), ("RDW-CV",             8),
    ("RDW-SD*", id_map.get("RDW_SD")),
    ("RDW-SD",  id_map.get("RDW_SD")),
    ("MPV",                10), ("MPV .",             10),
    ("P-LCR*",  id_map.get("PLCR")),
    ("P-LCR",   id_map.get("PLCR")),
    ("PCT*",               12), ("PCT",               12),
    ("PDW*",               11), ("PDW",               11),
    ("Neutrofile %.",      13), ("Neutrofile #.",      14),
    ("Limfocite %.",       15), ("Limfocite #.",       16),
    ("Monocite %.",        17), ("Monocite #.",        18),
    ("Eozinofile %.",      19), ("Eozinofile #.",      20),
    ("Bazofile %.",        21), ("Bazofile #.",        22),
    ("Granulocite imature % *", id_map.get("GRAN_IMT_PCT")),
    ("Granulocite imature # *", id_map.get("GRAN_IMT_NR")),
    ("Eritroblasti # *",  id_map.get("ERITROBL_NR")),
    ("Eritroblasti % *",  id_map.get("ERITROBL_PCT")),
]
noi = 0
for alias, sid in aliasuri:
    if not sid:
        continue
    cur.execute("SELECT id FROM analiza_alias WHERE LOWER(alias) = LOWER(%s)", (alias,))
    if not cur.fetchone():
        cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s, %s)", (alias, sid))
        noi += 1
print(f"   {noi} aliasuri noi adaugate.")

conn.commit()
print("\n✓ Gata!")

# Sumar final
cur.execute("SELECT COUNT(*) as t, COUNT(analiza_standard_id) as m FROM rezultate_analize WHERE buletin_id=32")
s = cur.fetchone()
print(f"B32 final: {s['t']} rezultate, {s['m']} mapate")
conn.close()
