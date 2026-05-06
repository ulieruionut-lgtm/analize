import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("=== NEMAPATE ===")
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate
    FROM rezultate_analize r
    WHERE r.buletin_id=34 AND r.analiza_standard_id IS NULL ORDER BY r.id
""")
for r in cur.fetchall():
    print(f"  RID={r['id']} raw='{r['denumire_raw']}' val={r['valoare']} vt='{r['valoare_text']}' unit={r['unitate']}")

print("\n=== Acid Uric / Bilirubina / eGFR in B34 ===")
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate, a.denumire_standard, a.cod_standard
    FROM rezultate_analize r
    JOIN analiza_standard a ON a.id=r.analiza_standard_id
    WHERE r.buletin_id=34 AND a.cod_standard IN ('ACID_URIC','BILIRUBINA_D','EGFR') ORDER BY r.id
""")
for r in cur.fetchall():
    print(f"  RID={r['id']} std={r['denumire_standard']} val={r['valoare']} unit={r['unitate']}")

print("\n=== TOATE mapate ===")
cur.execute("""
    SELECT r.id, r.valoare, r.valoare_text, r.unitate, a.denumire_standard
    FROM rezultate_analize r
    JOIN analiza_standard a ON a.id=r.analiza_standard_id
    WHERE r.buletin_id=34 ORDER BY r.id
""")
for r in cur.fetchall():
    val = r['valoare_text'] or str(r['valoare'])
    print(f"  {r['denumire_standard']:50s} = {val} {r['unitate'] or ''}")

conn.close()
