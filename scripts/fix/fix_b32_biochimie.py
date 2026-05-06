import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Ce avem in B32 pentru biochimie
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.unitate, a.denumire_standard, a.cod_standard
    FROM rezultate_analize r
    LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE r.buletin_id = 32
    ORDER BY r.id
""")
rez_b32 = {r['cod_standard']: r for r in cur.fetchall()}
print("Analize biochimie existente in B32:")
for cod, r in rez_b32.items():
    if cod in ['CREAT_URINA','MICROALBUMIN','RAPORT_ACU','ACID_URIC','CREATININA',
               'EGFR','GLICEMIE','COLESTEROL_TOTAL','TGL','HDL','LDL','PROT_TOTALE',
               'ALAT','CRP','NA','K','POTASIU','RFG']:
        print(f"  {r['cod_standard']:20s} | {r['denumire_standard']} = {r['valoare']} {r['unitate'] or ''}")

# ── Gaseste ID-uri necesare ────────────────────────────────────────────────────
print("\n--- Verific analize standard ---")
def get_std(cur, cod=None, like_den=None):
    if cod:
        cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard WHERE cod_standard = %s", (cod,))
    else:
        cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard WHERE LOWER(denumire_standard) LIKE %s ORDER BY id LIMIT 1", (f"%{like_den.lower()}%",))
    r = cur.fetchone()
    if r: print(f"  GASIT: ID={r['id']} | {r['denumire_standard']} | cod={r['cod_standard']}")
    else: print(f"  LIPSA: cod={cod or like_den}")
    return r

egfr_std     = get_std(cur, like_den="eGFR") or get_std(cur, like_den="RFG estimat")
hdl_std      = get_std(cur, like_den="HDL")
potasiu_std  = get_std(cur, like_den="Potasiu")
clearance_std = get_std(cur, like_den="Clearance")

# Adauga Clearance creatinina daca nu exista
if not clearance_std:
    cur.execute("INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES ('CLEARANCE_CR', 'Clearance creatinina (Cockcroft-Gault)') RETURNING id, cod_standard, denumire_standard")
    clearance_std = cur.fetchone()
    print(f"  CREAT NOU: {clearance_std['denumire_standard']} ID={clearance_std['id']}")

# ── Fix unitati gresite ────────────────────────────────────────────────────────
print("\n--- Corectez unitati gresite in B32 ---")
# Proteine totale: "g/di" -> "g/dL"
cur.execute("UPDATE rezultate_analize SET unitate='g/dL' WHERE buletin_id=32 AND LOWER(unitate)='g/di'")
if cur.rowcount: print(f"  FIX: unitate 'g/di' -> 'g/dL' ({cur.rowcount} randuri)")

# Densitate urinara: "OO" -> ""
cur.execute("UPDATE rezultate_analize SET unitate=NULL WHERE buletin_id=32 AND unitate='OO'")
if cur.rowcount: print(f"  FIX: unitate 'OO' -> NULL ({cur.rowcount} randuri)")

# Urobilinogen: "E.U/dI" -> "E.U/dL"
cur.execute("UPDATE rezultate_analize SET unitate='E.U/dL' WHERE buletin_id=32 AND LOWER(unitate) LIKE '%e.u%'")
if cur.rowcount: print(f"  FIX: unitate E.U/dI -> E.U/dL")

# ── Adauga analize lipsa ───────────────────────────────────────────────────────
print("\n--- Adaug analize lipsa din PDF ---")
def adauga_daca_lipseste(cur, buletin_id, std_id, raw, valoare, unitate, flag=None):
    cur.execute("SELECT id FROM rezultate_analize WHERE buletin_id=%s AND analiza_standard_id=%s", (buletin_id, std_id))
    if cur.fetchone():
        print(f"  EXISTA: {raw}")
        return
    cur.execute(
        "INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, unitate, flag) VALUES (%s,%s,%s,%s,%s,%s)",
        (buletin_id, std_id, raw, valoare, unitate, flag)
    )
    print(f"  ADAUGAT: {raw} = {valoare} {unitate or ''}")

# eGFR = 62.77 (in PDF: "- eGFR*")
if egfr_std:
    # Verifica daca valoarea existenta e corecta
    cur.execute("SELECT id, valoare FROM rezultate_analize WHERE buletin_id=32 AND analiza_standard_id=%s", (egfr_std['id'],))
    egfr_ex = cur.fetchone()
    if egfr_ex:
        if abs(egfr_ex['valoare'] - 62.77) > 0.01:
            cur.execute("UPDATE rezultate_analize SET valoare=62.77, unitate='mL/min/1.73m2' WHERE id=%s", (egfr_ex['id'],))
            print(f"  CORECTAT eGFR: {egfr_ex['valoare']} -> 62.77 mL/min/1.73m2")
        else:
            print(f"  OK: eGFR = {egfr_ex['valoare']}")
    else:
        adauga_daca_lipseste(cur, 32, egfr_std['id'], "- eGFR*", 62.77, "mL/min/1.73m2")

# Clearance creatinina = 54.33
adauga_daca_lipseste(cur, 32, clearance_std['id'], "- Clearance la creatinina*", 54.33, "mL/min")

# HDL Colesterol = 51.20
if hdl_std:
    adauga_daca_lipseste(cur, 32, hdl_std['id'], "Colesterol HDL", 51.20, "mg/dL")

# Potasiu seric = 4.00
if potasiu_std:
    adauga_daca_lipseste(cur, 32, potasiu_std['id'], "Potasiu seric", 4.00, "mmol/L")

# ── Aliasuri noi ───────────────────────────────────────────────────────────────
print("\n--- Adaug aliasuri ---")
aliasuri = [
    ("- eGFR*", egfr_std['id'] if egfr_std else None),
    ("eGFR*", egfr_std['id'] if egfr_std else None),
    ("Clearance la creatinina*", clearance_std['id']),
    ("Clearance creatinina", clearance_std['id']),
    ("Clearance la creatinina", clearance_std['id']),
    ("Colesterol HDL", hdl_std['id'] if hdl_std else None),
    ("Colesterol seric HDL", hdl_std['id'] if hdl_std else None),
    ("HDL Colesterol", hdl_std['id'] if hdl_std else None),
    ("Potasiu seric", potasiu_std['id'] if potasiu_std else None),
    ("POTASIU SERIC", potasiu_std['id'] if potasiu_std else None),
    ("TGP / ALT", 38),
    ("TGP/ALT", 38),
    ("Proteina C reactiva*", 87),
    ("Glucoza serica", 23),
    ("Acid uric seric", 32),
    ("Trigliceride serice", 34),
    ("Colesterol seric total", 43),
    ("Creatinina serica", 27),
]
noi = 0
for alias, sid in aliasuri:
    if not sid: continue
    cur.execute("SELECT id FROM analiza_alias WHERE LOWER(alias)=LOWER(%s)", (alias,))
    if not cur.fetchone():
        cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s,%s)", (alias, sid))
        print(f"  NOU: '{alias}'")
        noi += 1
if noi == 0: print("  Toate existau deja.")

conn.commit()
cur.execute("SELECT COUNT(*) as t, COUNT(analiza_standard_id) as m FROM rezultate_analize WHERE buletin_id=32")
s = cur.fetchone()
print(f"\n✓ B32 final: {s['t']} rezultate, {s['m']} mapate")
conn.close()
