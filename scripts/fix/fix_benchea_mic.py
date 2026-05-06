import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

BULETIN_ID = 34

# 1. HDL cu valoare=None si valoare_text=None -> sterge
cur.execute("""
    SELECT r.id FROM rezultate_analize r
    JOIN analiza_standard a ON a.id=r.analiza_standard_id
    WHERE r.buletin_id=%s AND a.cod_standard='HDL' AND r.valoare IS NULL AND r.valoare_text IS NULL
""", (BULETIN_ID,))
hdl_null = cur.fetchone()
if hdl_null:
    cur.execute("DELETE FROM rezultate_analize WHERE id=%s", (hdl_null['id'],))
    print(f"STERS HDL null RID={hdl_null['id']}")

# 2. Fix Leucocite urina "Negativ Negativ, <10/uL" -> "Negativ"
cur.execute("""
    SELECT r.id, r.valoare_text FROM rezultate_analize r
    WHERE r.buletin_id=%s AND r.valoare_text LIKE '%%Negativ Negativ%%'
""", (BULETIN_ID,))
for r in cur.fetchall():
    cur.execute("UPDATE rezultate_analize SET valoare_text='Negativ' WHERE id=%s", (r['id'],))
    print(f"FIX Leucocite urina valoare_text -> 'Negativ' (RID={r['id']})")

# 3. Sterge al doilea Eritrocite urina (duplicat)
cur.execute("""
    SELECT r.id, r.valoare_text, r.valoare FROM rezultate_analize r
    JOIN analiza_standard a ON a.id=r.analiza_standard_id
    WHERE r.buletin_id=%s AND a.cod_standard IN ('ERI','RBC') ORDER BY r.id
""", (BULETIN_ID,))
eri_all = cur.fetchall()
print(f"\nEritrocite B34: {len(eri_all)} intrari:")
eri_absente = [r for r in eri_all if r['valoare_text'] and 'Absente' in r['valoare_text']]
eri_numeric = [r for r in eri_all if r['valoare'] is not None]
print(f"  Absente: {len(eri_absente)}, Numerice: {len(eri_numeric)}")
for r in eri_all:
    print(f"  RID={r['id']} val={r['valoare']} vt='{r['valoare_text']}'")

# Pastreaza primul Absente (urina sumar), sterge al doilea daca exista
if len(eri_absente) > 1:
    for r in eri_absente[1:]:
        cur.execute("DELETE FROM rezultate_analize WHERE id=%s", (r['id'],))
        print(f"  STERS duplicat Eritrocite Absente RID={r['id']}")

conn.commit()
cur.execute("SELECT COUNT(*) as t, COUNT(analiza_standard_id) as m FROM rezultate_analize WHERE buletin_id=%s", (BULETIN_ID,))
s = cur.fetchone()
print(f"\n=== B{BULETIN_ID} FINAL: {s['t']} rezultate, {s['m']} mapate ===")
conn.close()
