import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)

conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Iancu e stocat ca "lancu" (l mic in loc de I)
cur.execute("SELECT id, nume FROM pacienti WHERE LOWER(nume) LIKE '%%ancu%%'")
p = cur.fetchone()
pacient_id = p['id']
print(f"Pacient: {p['nume']} (ID={pacient_id})")

# Toate buletinele
cur.execute("SELECT id, data_buletin FROM buletine WHERE pacient_id = %s ORDER BY data_buletin DESC", (pacient_id,))
buletine = cur.fetchall()
for b in buletine:
    print(f"\n=== Buletin B{b['id']} ({b['data_buletin'].date()}) ===")
    cur.execute("""
        SELECT r.id, r.denumire_raw, r.valoare, r.unitate, r.analiza_standard_id,
               a.denumire_standard
        FROM rezultate_analize r
        LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
        WHERE r.buletin_id = %s ORDER BY r.id
    """, (b['id'],))
    rezultate = cur.fetchall()
    for r in rezultate:
        std = r['denumire_standard'] or '--- NEMAPAT ---'
        print(f"  RID={r['id']:4d} | '{r['denumire_raw']}' -> {std} | val={r['valoare']} {r['unitate'] or ''}")

conn.close()
