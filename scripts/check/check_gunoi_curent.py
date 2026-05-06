# encoding: utf-8
import psycopg2, psycopg2.extras, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("=== TOATE analizele nerecunoscute (std IS NULL) ===")
cur.execute("""
    SELECT b.id as bid, b.data_buletin, p.cnp, p.nume,
           r.id as rid, r.denumire_raw, r.valoare, r.unitate
    FROM rezultate_analize r
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE r.analiza_standard_id IS NULL
    ORDER BY b.id, r.id
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  B{row['bid']} ({row['nume']}) rid={row['rid']} | [{row['denumire_raw']}] = {row['valoare']} {row['unitate'] or ''}")
else:
    print("  NICIUNA!")

print("\n=== Buletine Laza ===")
cur.execute("""
    SELECT b.id, b.data_buletin, COUNT(r.id) as total,
           SUM(CASE WHEN r.analiza_standard_id IS NULL THEN 1 ELSE 0 END) as gunoi
    FROM buletine b
    JOIN pacienti p ON p.id = b.pacient_id
    LEFT JOIN rezultate_analize r ON r.buletin_id = b.id
    WHERE p.cnp = '2780416131279'
    GROUP BY b.id, b.data_buletin
    ORDER BY b.id
""")
for row in cur.fetchall():
    print(f"  B{row['id']} | {str(row['data_buletin'])[:10]} | total={row['total']} | gunoi={row['gunoi']}")

conn.close()
