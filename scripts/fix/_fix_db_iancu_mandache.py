import psycopg2, psycopg2.extras
DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Iancu - 'lancu' e eroare OCR (I citit ca l)
cur.execute("UPDATE pacienti SET nume = %s WHERE cnp = %s", ("IANCU", "1420917080026"))
print(f"Iancu fix: {cur.rowcount} rand(uri)")

# Mandache - prenumele e duplicat (MANDACHE OANA ALEXANDRA / OANA ALEXANDRA)
# Deja e split corect: nume=MANDACHE OANA ALEXANDRA, prenume=OANA ALEXANDRA
# Corectam: nume=MANDACHE, prenume=OANA ALEXANDRA
cur.execute("UPDATE pacienti SET nume = %s, prenume = %s WHERE cnp = %s",
            ("MANDACHE", "OANA ALEXANDRA", "2970424080038"))
print(f"Mandache fix: {cur.rowcount} rand(uri)")

conn.commit()

print("\n=== Toti pacientii dupa fix ===")
cur.execute("SELECT id, cnp, COALESCE(nume,'') as n, COALESCE(prenume,'') as p FROM pacienti ORDER BY id")
for r in cur.fetchall():
    print(f"  [{r['id']}] {r['cnp']} | {r['n'][:50]} | {r['p'][:30]}")
conn.close()
print("\nOK - toti pacientii corectati.")
