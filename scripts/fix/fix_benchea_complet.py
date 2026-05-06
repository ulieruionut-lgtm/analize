import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

BULETIN_ID = 34

# Afiseaza cu RID-uri
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate, r.analiza_standard_id,
           a.denumire_standard, a.cod_standard
    FROM rezultate_analize r
    LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE r.buletin_id = %s ORDER BY r.id
""", (BULETIN_ID,))
toate = cur.fetchall()

# ── 1. IDENTIFICA GUNOI ────────────────────────────────────────────────────────
gunoi_rids = []
for r in toate:
    raw = r['denumire_raw'] or ''
    val = r['valoare']
    val_text = r['valoare_text'] or ''
    
    # Gunoi clar
    if raw in ['Pg.', 'k =', 'deschis', 'rare', 'rara', 'Clar', 'Negativ',
               'Absente Absente, Foarte', 'Absent Absent', 'Foarterare Foarte rare',
               'Galbendeschis Galben', 'Absenta Absenta, Foarte',
               'Negativ Negativ']:
        gunoi_rids.append(r['id'])
    # Note de referinta
    elif raw in ['Interpretare valori glicemie bazala (recomandari ADA)',
                 'TRIGLICERIDE 110 mg/dL <150', 'eGFR: 60 -', 'crescute \u2265',
                 'Absenti Absenti, \u2264']:
        gunoi_rids.append(r['id'])
    # eGFR duplicat cu valoare incorecta (142.0)
    elif r['cod_standard'] == 'EGFR' and val and val > 100:
        gunoi_rids.append(r['id'])
        print(f"  Gunoi eGFR duplicat: RID={r['id']} val={val}")

print(f"1. STERG {len(gunoi_rids)} intrari gunoi:")
for rid in gunoi_rids:
    cur.execute("SELECT denumire_raw FROM rezultate_analize WHERE id=%s", (rid,))
    row = cur.fetchone()
    cur.execute("DELETE FROM rezultate_analize WHERE id=%s", (rid,))
    print(f"   STERS RID={rid}: '{row['denumire_raw'] if row else '?'}'")

# ── 2. FIX MAPARE GRESITA: Acid uric -> Bilirubina directa ───────────────────
print("\n2. FIX mapari gresite:")
# Acid uric seric = 7.29 e mapat gresit ca Bilirubina directa
cur.execute("""
    SELECT r.id FROM rezultate_analize r
    JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE r.buletin_id = %s AND a.cod_standard = 'BILIRUBINA_D' AND r.valoare = 7.29
""", (BULETIN_ID,))
bil_row = cur.fetchone()
if bil_row:
    cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'ACID_URIC'")
    acid_std = cur.fetchone()
    if acid_std:
        cur.execute("UPDATE rezultate_analize SET analiza_standard_id=%s, denumire_raw='ACID URIC SERIC' WHERE id=%s",
                    (acid_std['id'], bil_row['id']))
        print(f"   FIX: Acid uric seric = 7.29 (era mapat gresit ca Bilirubina directa)")

# Bilirubina raw nemapat → map la Bilirubina urina
cur.execute("SELECT id FROM rezultate_analize WHERE buletin_id=%s AND denumire_raw='Bilirubina' AND analiza_standard_id IS NULL", (BULETIN_ID,))
bil_raw = cur.fetchone()
if bil_raw:
    cur.execute("UPDATE rezultate_analize SET analiza_standard_id=289, valoare_text='Negativ', valoare=NULL, unitate=NULL WHERE id=%s", (bil_raw['id'],))
    print(f"   FIX: Bilirubina urina = Negativ (RID={bil_raw['id']})")

# Albumina in urina spontana → Microalbuminurie
cur.execute("SELECT id FROM rezultate_analize WHERE buletin_id=%s AND LOWER(denumire_raw) LIKE '%%albumina in urina%%'", (BULETIN_ID,))
alb = cur.fetchone()
if alb:
    cur.execute("UPDATE rezultate_analize SET analiza_standard_id=129 WHERE id=%s", (alb['id'],))
    print(f"   FIX: Albumina in urina spontana -> Microalbuminurie")

# Creatinina in urina spontana → Creatinina urinara
cur.execute("SELECT id FROM rezultate_analize WHERE buletin_id=%s AND LOWER(denumire_raw) LIKE '%%creatinina in urina%%'", (BULETIN_ID,))
cr = cur.fetchone()
if cr:
    cur.execute("UPDATE rezultate_analize SET analiza_standard_id=130 WHERE id=%s", (cr['id'],))
    print(f"   FIX: Creatinina in urina spontana -> Creatinina urinara")

# ── 3. CURATA valoare_text care au text extra (referinte) ────────────────────
print("\n3. CURATA valoare_text cu text extra:")
def curata_val_text(cur, buletin_id, std_id, val_corecta):
    cur.execute("SELECT id, valoare_text FROM rezultate_analize WHERE buletin_id=%s AND analiza_standard_id=%s", (buletin_id, std_id))
    row = cur.fetchone()
    if row and row['valoare_text'] and row['valoare_text'] != val_corecta:
        cur.execute("UPDATE rezultate_analize SET valoare_text=%s WHERE id=%s", (val_corecta, row['id']))
        print(f"   FIX valoare_text std_id={std_id}: '{row['valoare_text'][:40]}' -> '{val_corecta}'")

curata_val_text(cur, BULETIN_ID, 290, "Normal")       # Urobilinogen
curata_val_text(cur, BULETIN_ID, 287, "Normal")       # Glucoza urina
curata_val_text(cur, BULETIN_ID, 288, "Absenti")      # Corpi cetonici
curata_val_text(cur, BULETIN_ID, 293, "Absente")      # Eritrocite urina (blood)
curata_val_text(cur, BULETIN_ID, 292, "Negativ")      # Leucocite urina
curata_val_text(cur, BULETIN_ID, 291, "Absenti")      # Nitriti
curata_val_text(cur, BULETIN_ID, 286, "Absente")      # Proteine urina

# ── 4. ADAUGA analize lipsa din urina ────────────────────────────────────────
print("\n4. ADAUG analize lipsa:")

# Adauga Claritate urina daca nu exista in standard
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='CLARITATE_URINA'")
clar_std = cur.fetchone()
if not clar_std:
    cur.execute("INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES ('CLARITATE_URINA', 'Claritate urina') RETURNING id")
    clar_std = cur.fetchone()
    print(f"   Adaugat analiza standard: Claritate urina (ID={clar_std['id']})")

# Adauga Celule epiteliale rotunde daca nu exista
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='CEL_EPITEL_ROTUNDE'")
cer_std = cur.fetchone()
if not cer_std:
    cur.execute("INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES ('CEL_EPITEL_ROTUNDE', 'Celule epiteliale rotunde urina') RETURNING id")
    cer_std = cur.fetchone()
    print(f"   Adaugat analiza standard: Celule epiteliale rotunde (ID={cer_std['id']})")

# Adauga Mucus urina daca nu exista
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='MUCUS_URINA'")
muc_std = cur.fetchone()
if not muc_std:
    cur.execute("INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES ('MUCUS_URINA', 'Mucus urina') RETURNING id")
    muc_std = cur.fetchone()
    print(f"   Adaugat analiza standard: Mucus urina (ID={muc_std['id']})")

# Adauga Leucocite sediment urina daca nu exista (diferit de Leucocite urina din sumar)
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='LEUCOCITE_SED'")
leu_sed = cur.fetchone()
if not leu_sed:
    cur.execute("INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES ('LEUCOCITE_SED', 'Leucocite sediment urinar') RETURNING id")
    leu_sed = cur.fetchone()

def adauga_daca_lipseste(cur, bul_id, std_id, raw, valoare, valoare_text, unitate):
    cur.execute("SELECT id FROM rezultate_analize WHERE buletin_id=%s AND analiza_standard_id=%s", (bul_id, std_id))
    if cur.fetchone():
        print(f"   EXISTA: {raw}")
        return
    cur.execute(
        "INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate) VALUES (%s,%s,%s,%s,%s,%s)",
        (bul_id, std_id, raw, valoare, valoare_text, unitate)
    )
    val_afis = valoare_text or str(valoare)
    print(f"   ADAUGAT: {raw} = {val_afis}")

adauga_daca_lipseste(cur, BULETIN_ID, 284, "pH urinar",           6.0,    None,           None)
adauga_daca_lipseste(cur, BULETIN_ID, 285, "Densitate urinara",   1008.0, None,           None)
adauga_daca_lipseste(cur, BULETIN_ID, 295, "Culoare*",            None,   "Galben deschis", None)
adauga_daca_lipseste(cur, BULETIN_ID, clar_std['id'], "Claritate*", None, "Clar",         None)
adauga_daca_lipseste(cur, BULETIN_ID, 300, "Celule epiteliale plate", None, "Foarte rare", None)
adauga_daca_lipseste(cur, BULETIN_ID, leu_sed['id'], "Leucocite sediment", None, "Foarte rare", None)
adauga_daca_lipseste(cur, BULETIN_ID, cer_std['id'], "Celule epiteliale rotunde", None, "Absente", None)
adauga_daca_lipseste(cur, BULETIN_ID, 294, "Flora bacteriana",    None,   "Absenta",      None)
adauga_daca_lipseste(cur, BULETIN_ID, muc_std['id'], "Mucus",     None,   "Absent",       None)

# ── 5. ALIASURI NOI ───────────────────────────────────────────────────────────
print("\n5. ADAUG aliasuri noi:")
aliasuri = [
    ("ACID URIC SERIC",            32),
    ("Acid uric seric",            32),
    ("ALANINAMINOTRANSFERAZA (ALT/GPT/TGP)", 38),
    ("ASPARTATAMINOTRANSFERAZA (GOT/AST/TGO)", 39),
    ("HDL COLESTEROL",             44),
    ("LDL COLESTEROL",             45),
    ("CREATININA SERICA",          27),
    ("Rata estimata a filtrarii glomerulare (eGFR)*", 37),
    ("GLUCOZA SERICA (GLICEMIE)",  23),
    ("POTASIU SERIC",              50),
    ("SODIU SERIC",                49),
    ("Albumina in urina spontana", 129),
    ("Creatinina in urina spontana", 130),
    ("Raport albumina / creatinina - urina spontana", 301),
    ("Raport albumina/creatinina - urina spontana (RAC)", 301),
    ("Culoare*",                   295),
    ("Culoare urina",              295),
    ("Claritate*",                 clar_std['id']),
    ("Claritate urina",            clar_std['id']),
    ("Celule epiteliale plate",    300),
    ("Celule epiteliale rotunde",  cer_std['id']),
    ("Flora bacteriana",           294),
    ("Mucus",                      muc_std['id']),
    ("Leucocite sediment",         leu_sed['id']),
    ("FT4 (TIROXINA LIBERA)",      65),
    ("TSH (HORMON DE STIMULARE TIROIDIANA)", 64),
    ("Bilirubina",                 289),
    ("PH",                         284),
    ("pH urinar",                  284),
]
noi = 0
for alias, sid in aliasuri:
    cur.execute("SELECT id FROM analiza_alias WHERE LOWER(alias)=LOWER(%s)", (alias,))
    if not cur.fetchone():
        cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s,%s)", (alias, sid))
        print(f"   NOU: '{alias}'")
        noi += 1
if noi == 0: print("   Toate existau.")

conn.commit()
cur.execute("SELECT COUNT(*) as t, COUNT(analiza_standard_id) as m FROM rezultate_analize WHERE buletin_id=%s", (BULETIN_ID,))
s = cur.fetchone()
print(f"\n✓ B{BULETIN_ID} final: {s['t']} rezultate, {s['m']} mapate")
conn.close()
