import psycopg2, os
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

for bid in [18, 19]:
    cur.execute("SELECT COUNT(*) FROM rezultate_analize WHERE buletin_id=%s", (bid,))
    total = cur.fetchone()[0]
    cur.execute("""
        SELECT r.denumire_raw, r.valoare, r.unitate, a.cod_standard
        FROM rezultate_analize r
        LEFT JOIN analiza_standard a ON a.id=r.analiza_standard_id
        WHERE r.buletin_id=%s
        AND (a.cod_standard IN ('HGB','HCT','MCH','MCHC') OR r.analiza_standard_id IS NULL)
        ORDER BY a.cod_standard NULLS LAST
    """, (bid,))
    rows = cur.fetchall()
    print(f"Buletin {bid}: {total} analize total")
    for r in rows:
        print(f"  [{r[3] or 'NEMAPAT'}] {r[0]} = {r[1]} {r[2] or ''}")
    print()

conn.close()
