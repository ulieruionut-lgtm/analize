import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("SELECT id, nume FROM pacienti WHERE LOWER(nume) LIKE '%%nitu%%'")
p = cur.fetchone()
print(f"Pacient: {p['nume']} (ID={p['id']})")

cur.execute("SELECT id, data_buletin FROM buletine WHERE pacient_id=%s ORDER BY data_buletin DESC", (p['id'],))
b = cur.fetchone()
print(f"Buletin: B{b['id']} ({b['data_buletin'].date() if b['data_buletin'] else 'N/A'})")

cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate,
           a.denumire_standard, a.cod_standard
    FROM rezultate_analize r
    LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE r.buletin_id = %s ORDER BY r.id
""", (b['id'],))
rez = cur.fetchall()
print(f"\nTotal rezultate: {len(rez)}\n")
for r in rez:
    std = r['denumire_standard'] or '!!! NEMAPAT'
    val = r['valoare_text'] if r['valoare_text'] else str(r['valoare'])
    mark = "  " if r['denumire_standard'] else "!!"
    print(f"{mark} {std:50s} = {val} {r['unitate'] or ''}")
    if not r['denumire_standard']:
        print(f"    RAW: '{r['denumire_raw']}'")
conn.close()
