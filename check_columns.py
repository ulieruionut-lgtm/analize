import psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()
for tabel in ['rezultate_analize', 'analiza_alias']:
    cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{tabel}' ORDER BY ordinal_position")
    cols = [r[0] for r in cur.fetchall()]
    print(f"{tabel}: {cols}")
conn.close()
