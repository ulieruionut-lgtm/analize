import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("SELECT id, nume FROM pacienti WHERE LOWER(nume) LIKE '%%benchea%%'")
p = cur.fetchone()
if not p:
    print("Benchea nu exista in DB!")
    conn.close()
    sys.exit(0)

print(f"Pacient: {p['nume']} (ID={p['id']})")
cur.execute("SELECT id, data_buletin, created_at FROM buletine WHERE pacient_id=%s ORDER BY data_buletin DESC", (p['id'],))
buletine = cur.fetchall()
print(f"Buletine: {len(buletine)}")

for b in buletine:
    cur.execute("""
        SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate,
               a.denumire_standard, a.cod_standard
        FROM rezultate_analize r
        LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
        WHERE r.buletin_id = %s ORDER BY r.id
    """, (b['id'],))
    rez = cur.fetchall()
    # re-query cu analiza_standard_id
    cur.execute("SELECT COUNT(*) as tot, COUNT(analiza_standard_id) as map FROM rezultate_analize WHERE buletin_id=%s", (b['id'],))
    cnt = cur.fetchone()
    print(f"\n=== B{b['id']} ({b['data_buletin'].date() if b['data_buletin'] else 'N/A'}) | {cnt['tot']} rezultate, {cnt['map']} mapate ===")
    for r in rez:
        std = r['denumire_standard'] or '!!! NEMAPAT'
        val = r['valoare_text'] if r['valoare_text'] else str(r['valoare'])
        mark = "  " if r['denumire_standard'] else "!!"
        print(f"  {mark} {std:45s} | {val} {r['unitate'] or ''}")
        if not r['denumire_standard']:
            print(f"      RAW: '{r['denumire_raw']}'")

conn.close()
