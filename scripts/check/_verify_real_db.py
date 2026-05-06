import psycopg2
conn = psycopg2.connect("postgresql://postgres:VGPXzrHKFpNWXogyQqnevLvZAwlgpVKu@maglev.proxy.rlwy.net:48480/railway")
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='rezultate_analize' ORDER BY ordinal_position")
cols = [r[0] for r in cur.fetchall()]
print("Coloane:", cols)
cur.execute("SELECT COUNT(*) FROM pacienti")
print("Pacienti:", cur.fetchone()[0])
conn.close()
