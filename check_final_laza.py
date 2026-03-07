import psycopg2, psycopg2.extras

DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
SELECT b.id, b.data_buletin,
       COUNT(r.id) as total,
       SUM(CASE WHEN r.analiza_standard_id IS NOT NULL THEN 1 ELSE 0 END) as recunoscute,
       SUM(CASE WHEN r.analiza_standard_id IS NULL THEN 1 ELSE 0 END) as nerecunoscute
FROM buletine b
JOIN pacienti p ON b.pacient_id = p.id
LEFT JOIN rezultate_analize r ON r.buletin_id = b.id
WHERE p.cnp = '2780416131279'
GROUP BY b.id, b.data_buletin
ORDER BY b.id
""")
for row in cur.fetchall():
    bid = row["id"]
    data = str(row["data_buletin"])[:10]
    total = row["total"]
    rec = row["recunoscute"]
    nerec = row["nerecunoscute"]
    print(f"Buletin ID={bid} | {data} | total={total} | recunoscute={rec} | nerecunoscute={nerec}")

print("\nAnalize nerecunoscute ramase:")
cur.execute("""
SELECT b.id as bid, r.id as rid, r.denumire_raw, r.valoare
FROM rezultate_analize r
JOIN buletine b ON b.id = r.buletin_id
JOIN pacienti p ON p.id = b.pacient_id
WHERE p.cnp = '2780416131279' AND r.analiza_standard_id IS NULL
ORDER BY b.id, r.id
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  B{row['bid']} rid={row['rid']} | [{row['denumire_raw']}] = {row['valoare']}")
else:
    print("  NICIUNA! Toate analizele sunt recunoscute.")

conn.close()
