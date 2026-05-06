import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
BULETIN_ID = 8

# ── Helper ────────────────────────────────────────────────────────────────────
def get_std(cod):
    cur.execute("SELECT id, denumire_standard FROM analiza_standard WHERE cod_standard=%s", (cod,))
    r = cur.fetchone()
    if not r: raise ValueError(f"COD NEGASIT: {cod}")
    return r

def alias(a, sid):
    cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (a, sid))
    if cur.rowcount > 0: print(f"   ALIAS: '{a}'")

def rez(std_id, raw, valoare, valoare_text, unitate):
    cur.execute("SELECT id FROM rezultate_analize WHERE buletin_id=%s AND analiza_standard_id=%s", (BULETIN_ID, std_id))
    if cur.fetchone():
        return  # exista deja
    cur.execute("INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, valoare_text, unitate) VALUES (%s,%s,%s,%s,%s,%s)",
                (BULETIN_ID, std_id, raw, valoare, valoare_text, unitate))
    val = valoare_text or str(valoare)
    print(f"   ADAUGAT: {raw} = {val} {unitate or ''}")

# ── 0. Sterge duplicat PCR creat din greseala ─────────────────────────────────
cur.execute("DELETE FROM analiza_standard WHERE cod_standard='PCR'")
if cur.rowcount > 0: print("0. STERS duplicat analiza_standard PCR (cod=PCR)")
cur.execute("DELETE FROM analiza_alias WHERE alias IN ('PCR','Proteina C reactiva','Proteina C Reactiva','CRP','CRP ultrasensibil','hs-CRP')")

# ── 1. Adauga aliasuri pentru Proteina C reactiva (cod=CRP, ID=87) ───────────
crp_id = 87
print("1. Aliasuri Proteina C reactiva:")
for a in ['Proteina C reactiva', 'Proteina C Reactiva', 'PCR', 'CRP', 'hs-CRP', 'CRP (Proteina C reactiva)']:
    alias(a, crp_id)

# ── 2. Adaug analizele lipsa ─────────────────────────────────────────────────
print("\n2. Adaug analizele lipsa:")

rbc   = get_std('RBC')
hb    = get_std('HB')
hct   = get_std('HCT')
mcv   = get_std('MCV')
mch   = get_std('MCH')
mchc  = get_std('MCHC')
rdw   = get_std('RDW')
plt   = get_std('PLT')
wbc   = get_std('WBC')
neu_nr = get_std('NEUTROFILE_NR')
lym_nr = get_std('LIMFOCITE_NR')
mon_nr = get_std('MONOCITE_NR')
eos_nr = get_std('EOZINOFILE_NR')
bas_nr = get_std('BAZOFILE_NR')

# Hematii 4.650.000/mm³ = 4.65 mil./µL
rez(rbc['id'],   'Hematii',      4.65,  None, 'mil./µL')
# Hemoglobina 13.3 g/dL
rez(hb['id'],    'Hemoglobina',  13.3,  None, 'g/dL')
# Hematocrit 38.1 %
rez(hct['id'],   'Hematocrit',   38.1,  None, '%')
# MCV 81.9 fL
rez(mcv['id'],   'MCV',          81.9,  None, 'fL')
# MCH 28.6 pg
rez(mch['id'],   'MCH',          28.6,  None, 'pg')
# MCHC 34.9 g/dL
rez(mchc['id'],  'MCHC',         34.9,  None, 'g/dL')
# RDW 13.1 %
rez(rdw['id'],   'RDW',          13.1,  None, '%')
# Trombocite 323.000/mm³ = 323 mii/µL
rez(plt['id'],   'Trombocite',   323.0, None, 'mii/µL')
# Leucocite 3.980/mm³ = 3.98 mii/µL
rez(wbc['id'],   'Leucocite',    3.98,  None, 'mii/µL')

# Formula leucocitara - valori absolute
# Neutrofile 2.260/mm³ = 2.26 mii/µL
rez(neu_nr['id'], 'Neutrofile', 2.26,  None, 'mii/µL')
# Limfocite 1.150/mm³ = 1.15 mii/µL
rez(lym_nr['id'], 'Limfocite',  1.15,  None, 'mii/µL')
# Monocite 460/mm³ = 0.46 mii/µL
rez(mon_nr['id'], 'Monocite',   0.46,  None, 'mii/µL')
# Eozinofile 60/mm³ = 0.06 mii/µL
rez(eos_nr['id'], 'Eozinofile', 0.06,  None, 'mii/µL')
# Bazofile 50/mm³ = 0.05 mii/µL
rez(bas_nr['id'], 'Bazofile',   0.05,  None, 'mii/µL')

# Proteina C reactiva = 22.60 mg/L
rez(crp_id,       'Proteina C reactiva', 22.60, None, 'mg/L')

# ── 3. Aliasuri pentru formatul acestui laborator ────────────────────────────
print("\n3. Aliasuri suplimentare:")
for a in ['Hematii', 'Hematii (RBC)']:
    alias(a, rbc['id'])
for a in ['Hemoglobina', 'Hemoglobin', 'HGB']:
    alias(a, hb['id'])
for a in ['Hematocrit', 'Ht']:
    alias(a, hct['id'])
for a in ['Trombocite', 'Trombocite (PLT)']:
    alias(a, plt['id'])
for a in ['Leucocite', 'Leucocite (WBC)']:
    alias(a, wbc['id'])
for a in ['Neutrofile', 'Neutrofile nr.', 'Neutrofile absolute']:
    alias(a, neu_nr['id'])
for a in ['Limfocite', 'Limfocite nr.', 'Limfocite absolute']:
    alias(a, lym_nr['id'])
for a in ['Monocite', 'Monocite nr.', 'Monocite absolute']:
    alias(a, mon_nr['id'])
for a in ['Eozinofile', 'Eozinofile nr.', 'Eozinofile absolute']:
    alias(a, eos_nr['id'])
for a in ['Bazofile', 'Bazofile nr.', 'Bazofile absolute']:
    alias(a, bas_nr['id'])
for a in ['TGP (ALAT)', 'TGP', 'ALT (TGP)', 'ALAT (TGP)']:
    alias(a, get_std('ALT')['id'])
for a in ['Creatinina serică', 'Creatinina serica', 'Creatinina']:
    alias(a, get_std('CREATININA')['id'])

conn.commit()

# ── 4. Afisare finala ─────────────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) as t, COUNT(analiza_standard_id) as m FROM rezultate_analize WHERE buletin_id=%s", (BULETIN_ID,))
s = cur.fetchone()
print(f"\n=== B{BULETIN_ID} FINAL: {s['t']} rezultate, {s['m']} mapate ===\n")

cur.execute("""
    SELECT r.valoare, r.valoare_text, r.unitate, a.denumire_standard
    FROM rezultate_analize r
    JOIN analiza_standard a ON a.id=r.analiza_standard_id
    WHERE r.buletin_id=%s ORDER BY r.id
""", (BULETIN_ID,))
for r in cur.fetchall():
    val = r['valoare_text'] or str(r['valoare'])
    print(f"  {r['denumire_standard']:50s} = {val} {r['unitate'] or ''}")

conn.close()
