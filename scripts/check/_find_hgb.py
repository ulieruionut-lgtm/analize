import psycopg2, psycopg2.extras
DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Cauta Hemoglobina in analiza_standard
cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard WHERE LOWER(denumire_standard) LIKE '%hemoglobin%' ORDER BY id LIMIT 5")
rows = cur.fetchall()
for r in rows:
    print(r['id'], r['cod_standard'], r['denumire_standard'])

cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard WHERE LOWER(cod_standard) IN ('hgb', 'hb', 'hemoglobina') ORDER BY id LIMIT 5")
rows2 = cur.fetchall()
for r in rows2:
    print(r['id'], r['cod_standard'], r['denumire_standard'])

conn.close()
