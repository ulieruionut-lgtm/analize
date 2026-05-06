# encoding: utf-8
import psycopg2, psycopg2.extras, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

for bid in [23, 24, 15]:
    cur.execute("""
        SELECT r.id as rid, r.analiza_standard_id, ast.cod_standard, r.denumire_raw, r.valoare
        FROM rezultate_analize r
        LEFT JOIN analiza_standard ast ON ast.id = r.analiza_standard_id
        WHERE r.buletin_id = %s
        ORDER BY r.id
    """, (bid,))
    rows = cur.fetchall()
    print(f"\n=== Buletin ID={bid} ({len(rows)} analize) ===")
    for row in rows:
        flag = "GUNOI" if row['analiza_standard_id'] is None else "ok"
        print(f"  [{flag}] rid={row['rid']} | std={row['cod_standard']} | [{row['denumire_raw']}] = {row['valoare']}")

conn.close()
