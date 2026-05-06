import psycopg2, os
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Cauta HGB, MCH, VSH in buletin_id=4
cur.execute("SELECT id, denumire_raw, valoare, unitate FROM rezultate_analize WHERE buletin_id=4 ORDER BY id")
rows = cur.fetchall()
print(f"Total randuri buletin 4: {len(rows)}\n")
print("Cautare HGB/MCH/VSH:")
for r in rows:
    dn = str(r[1]).lower()
    if any(x in dn for x in ['hgb','hemoglobin','mch','vsh','hematii','viteza']):
        print(" GASIT:", r)

# Cauta in analiza_necunoscuta
cur.execute("SELECT id, denumire_raw, aparitii, aprobata FROM analiza_necunoscuta ORDER BY id DESC LIMIT 30")
print("\nUltimele 30 analize necunoscute:")
for r in cur.fetchall():
    print(f"  id={r[0]}, aparitii={r[2]}, aprobata={r[3]}: {r[1]}")

conn.close()
