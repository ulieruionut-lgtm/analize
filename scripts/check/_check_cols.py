import psycopg2
conn = psycopg2.connect("postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway")
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='rezultate_analize' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
print("Coloane in rezultate_analize:")
for c in cols:
    print(" -", c)
conn.close()
