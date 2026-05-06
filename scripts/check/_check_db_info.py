import psycopg2

# Conectare prin URL public
conn = psycopg2.connect("postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway")
cur = conn.cursor()

# Verifica coloana
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name='rezultate_analize' 
    ORDER BY ordinal_position
""")
cols = [r[0] for r in cur.fetchall()]
print("Coloane:", cols)

# Verifica cati pacienti are
cur.execute("SELECT COUNT(*) FROM pacienti")
print("Pacienti:", cur.fetchone()[0])

# Verifica cate buletine are
cur.execute("SELECT COUNT(*) FROM buletine")
print("Buletine:", cur.fetchone()[0])

# Verifica cate rezultate are
cur.execute("SELECT COUNT(*) FROM rezultate_analize")
print("Rezultate:", cur.fetchone()[0])

# Verifica DB name si server
cur.execute("SELECT current_database(), inet_server_addr(), inet_server_port()")
row = cur.fetchone()
print(f"DB: {row[0]}, Server: {row[1]}:{row[2]}")

conn.close()
