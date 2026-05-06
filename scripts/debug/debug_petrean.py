import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding="utf-8")
DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Cauta Petrean
cur.execute("SELECT id, cnp, nume, prenume FROM pacienti WHERE LOWER(nume) LIKE '%petrean%'")
rows = cur.fetchall()
print("Pacienti Petrean:")
for r in rows:
    print(f"  id={r['id']} cnp={r['cnp']} nume={r['nume']} prenume={r['prenume']}")
    pid = r['id']
    cur.execute("SELECT id FROM buletine WHERE pacient_id = %s", (pid,))
    buletine = cur.fetchall()
    print(f"  -> {len(buletine)} buletine: {[b['id'] for b in buletine]}")

conn.close()
