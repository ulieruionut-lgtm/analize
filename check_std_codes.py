import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard ORDER BY cod_standard")
for r in cur.fetchall():
    print(f"  ID={r['id']:3d} cod={r['cod_standard']:25s} {r['denumire_standard']}")
conn.close()
