import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='analiza_necunoscuta'")
print("Coloane analiza_necunoscuta:", [r['column_name'] for r in cur.fetchall()])
cur.execute("SELECT * FROM analiza_necunoscuta LIMIT 5")
rows = cur.fetchall()
print(f"Total randuri (sample 5): {len(rows)}")
for r in rows:
    print(" ", dict(r))
conn.close()
