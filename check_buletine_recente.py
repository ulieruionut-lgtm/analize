import psycopg2, psycopg2.extras

DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Ultimele buletine adaugate
print("=== Ultimele 10 buletine adaugate ===")
cur.execute("""
    SELECT b.id, b.data_buletin, b.fisier_original, p.cnp, p.nume,
           COUNT(r.id) as total_analize,
           SUM(CASE WHEN r.analiza_standard_id IS NULL THEN 1 ELSE 0 END) as nerecunoscute
    FROM buletine b
    JOIN pacienti p ON p.id = b.pacient_id
    LEFT JOIN rezultate_analize r ON r.buletin_id = b.id
    GROUP BY b.id, b.data_buletin, b.fisier_original, p.cnp, p.nume
    ORDER BY b.id DESC
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  B{row['id']} | {str(row['data_buletin'])[:10]} | {row['nume']} | total={row['total_analize']} | gunoi={row['nerecunoscute']} | {row['fisier_original']}")

# Cauta toate intrarile nerecunoscute din ultimele buletine
print("\n=== Analize nerecunoscute din ultimele 5 buletine ===")
cur.execute("""
    SELECT b.id as bid, b.data_buletin, p.nume, r.id as rid, r.denumire_raw, r.valoare
    FROM rezultate_analize r
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE r.analiza_standard_id IS NULL
    AND b.id IN (SELECT id FROM buletine ORDER BY id DESC LIMIT 5)
    ORDER BY b.id DESC, r.id
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  B{row['bid']} ({row['nume']}) rid={row['rid']} | [{row['denumire_raw']}] = {row['valoare']}")
else:
    print("  Nicio analiza nerecunoscuta in ultimele 5 buletine.")

conn.close()
