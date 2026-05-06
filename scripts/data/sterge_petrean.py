import sys, psycopg2
sys.stdout.reconfigure(encoding="utf-8")
DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Sterge Petrean (id=7, 0 buletine)
cur.execute("DELETE FROM pacienti WHERE id = 7")
print(f"Rand(uri) sterse din pacienti: {cur.rowcount}")
conn.commit()
conn.close()
print("Gata - Petrean sters.")
