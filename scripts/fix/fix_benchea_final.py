import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

BULETIN_ID = 34

# 1. Sterge vechile intrari nemapate (au duplicat corect adaugat)
print("1. STERG intrari vechi nemapate cu text extra:")
rids_vechi = [1108, 1110, 1113, 1115, 1116]
for rid in rids_vechi:
    cur.execute("SELECT denumire_raw FROM rezultate_analize WHERE id=%s AND buletin_id=34", (rid,))
    r = cur.fetchone()
    if r:
        cur.execute("DELETE FROM rezultate_analize WHERE id=%s", (rid,))
        print(f"   STERS RID={rid}: '{r['denumire_raw']}'")

# 2. Fix Bilirubina directa 7.29 -> Acid uric
print("\n2. FIX Acid Uric (mapat gresit):")
cur.execute("SELECT id, cod_standard FROM analiza_standard WHERE LOWER(denumire_standard) LIKE '%%acid uric%%'")
au_std = cur.fetchone()
print(f"   Acid uric standard: {au_std}")
if au_std:
    cur.execute("""
        UPDATE rezultate_analize
        SET analiza_standard_id=%s, denumire_raw='ACID URIC SERIC'
        WHERE buletin_id=%s AND valoare=7.29
          AND analiza_standard_id IN (SELECT id FROM analiza_standard WHERE LOWER(denumire_standard) LIKE '%%bilirubina%%')
    """, (au_std['id'], BULETIN_ID))
    print(f"   Actualizat {cur.rowcount} randuri")
    
    # Daca nu a prins (mapping diferit), cauta direct
    if cur.rowcount == 0:
        cur.execute("SELECT id, analiza_standard_id, denumire_raw FROM rezultate_analize WHERE buletin_id=%s AND valoare=7.29", (BULETIN_ID,))
        rows = cur.fetchall()
        for r in rows:
            cur2 = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur2.execute("SELECT denumire_standard FROM analiza_standard WHERE id=%s", (r['analiza_standard_id'],))
            std = cur2.fetchone()
            print(f"   7.29 mapat ca: {std['denumire_standard'] if std else 'NONE'} raw='{r['denumire_raw']}'")
            if std and 'bilirubina' in std['denumire_standard'].lower():
                cur.execute("UPDATE rezultate_analize SET analiza_standard_id=%s, denumire_raw='ACID URIC SERIC' WHERE id=%s",
                            (au_std['id'], r['id']))
                print(f"   FIX Acid uric: RID={r['id']}")

# 3. Fix HDL valoare_text (primul entry cu "Scazut...")
print("\n3. FIX HDL colesterol (sterge valoare_text de interpretare):")
cur.execute("""
    SELECT id, valoare, valoare_text FROM rezultate_analize 
    WHERE buletin_id=%s AND analiza_standard_id=(SELECT id FROM analiza_standard WHERE cod_standard='HDL')
    ORDER BY id
""", (BULETIN_ID,))
hdl_rows = cur.fetchall()
for r in hdl_rows:
    if r['valoare_text'] and 'Scazut' in r['valoare_text']:
        cur.execute("UPDATE rezultate_analize SET valoare_text=NULL WHERE id=%s", (r['id'],))
        print(f"   FIX HDL: sterse valoare_text cu 'Scazut...' (RID={r['id']})")
    elif r['valoare'] == 40.7:
        print(f"   OK HDL = {r['valoare']} mg/dL")

# 4. Fix Eritrocite si Leucocite din urina cu valoare_text extra
print("\n4. FIX valoare_text extra din urina:")
fixes = [
    # (std_cod, valoare_text_corecta, old_text_fragment)
    ('ERI_URINA', 'Absente', 'Absente, <10/uL'),  # Eritrocite urina din sumar
    ('LEU_URINA', 'Negativ', 'Negativ, <10/uL'),   # Leucocite urina
]
# Mai simplu - cauta dupa pattern
cur.execute("""
    SELECT r.id, r.valoare_text, a.cod_standard, a.denumire_standard
    FROM rezultate_analize r JOIN analiza_standard a ON a.id=r.analiza_standard_id
    WHERE r.buletin_id=%s AND r.valoare_text IS NOT NULL
      AND (r.valoare_text LIKE '%%Absente Absente%%' OR r.valoare_text LIKE '%%Negativ Negativ%%'
           OR r.valoare_text LIKE '%%<10/uL%%')
""", (BULETIN_ID,))
for r in cur.fetchall():
    vt = r['valoare_text']
    if 'Absente Absente' in vt or 'Absente, <10/uL' in vt or '<10/uL' in vt:
        # Eritrocite sau alte Absente
        if 'Absente' in vt:
            cur.execute("UPDATE rezultate_analize SET valoare_text='Absente' WHERE id=%s", (r['id'],))
            print(f"   FIX: {r['denumire_standard']} -> 'Absente' (era '{vt[:40]}')")
    elif 'Negativ Negativ' in vt or 'Negativ, <10/uL' in vt:
        cur.execute("UPDATE rezultate_analize SET valoare_text='Negativ' WHERE id=%s", (r['id'],))
        print(f"   FIX: {r['denumire_standard']} -> 'Negativ' (era '{vt[:40]}')")

# Sterge duplicatul de eritrocite din sediment cu text "Absente Absente, Foarte"
cur.execute("""
    SELECT r.id, r.valoare_text FROM rezultate_analize r
    JOIN analiza_standard a ON a.id=r.analiza_standard_id
    WHERE r.buletin_id=%s AND a.cod_standard='ERI' AND r.valoare_text IS NOT NULL
""", (BULETIN_ID,))
eri_rows = cur.fetchall()
print(f"\n5. Eritrocite in B34: {len(eri_rows)} intrari cu valoare_text:")
for r in eri_rows:
    print(f"   RID={r['id']} vt='{r['valoare_text']}'")
    if r['valoare_text'] and ('Absente, Foarte' in r['valoare_text'] or 'Absente Absente' in r['valoare_text']):
        cur.execute("DELETE FROM rezultate_analize WHERE id=%s", (r['id'],))
        print(f"   STERS RID={r['id']} (duplicat din sediment)")

conn.commit()
cur.execute("SELECT COUNT(*) as t, COUNT(analiza_standard_id) as m FROM rezultate_analize WHERE buletin_id=%s", (BULETIN_ID,))
s = cur.fetchone()
print(f"\n=== B{BULETIN_ID} FINAL: {s['t']} rezultate, {s['m']} mapate ===")
conn.close()
