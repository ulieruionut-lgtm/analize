import psycopg2, psycopg2.extras
DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("UPDATE pacienti SET prenume = %s WHERE cnp = %s", ("GHEORGHE", "1420917080026"))
print(f"Iancu prenume: {cur.rowcount} rand actualizat")

conn.commit()

cur.execute("SELECT id, cnp, nume, prenume FROM pacienti ORDER BY id")
for r in cur.fetchall():
    print(f"  [{r['id']}] {r['cnp']} | {r['nume']} | {r['prenume']}")
conn.close()
