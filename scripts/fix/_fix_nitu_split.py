import psycopg2, psycopg2.extras
DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Nitu - numele are "NITU MATEI" dar trebuie "NITU" cu prenume "MATEI"
cur.execute("UPDATE pacienti SET nume = %s, prenume = %s WHERE cnp = %s",
            ("NITU", "MATEI", "5240222080031"))
print(f"Nitu fix: {cur.rowcount} rand actualizat")

conn.commit()

cur.execute("SELECT id, cnp, nome, prenume FROM pacienti ORDER BY id")

print("\n=== Lista finala pacienti ===")
cur.execute("SELECT id, cnp, COALESCE(nume,'') as n, COALESCE(prenume,'') as p FROM pacienti ORDER BY id")
for r in cur.fetchall():
    print(f"  [{r['id']}] {r['cnp']} | {r['n']} | {r['p']}")
conn.close()
