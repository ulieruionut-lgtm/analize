import psycopg2, psycopg2.extras
DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Verifica ce coduri exista pentru Urobilinogen si Nitriti
cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard WHERE LOWER(denumire_standard) LIKE '%urobilinogen%' OR LOWER(denumire_standard) LIKE '%nitrit%' ORDER BY id")
for r in cur.fetchall():
    print(r['id'], r['cod_standard'], r['denumire_standard'])

conn.close()
