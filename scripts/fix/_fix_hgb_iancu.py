import psycopg2, psycopg2.extras
DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = %s", ("HB",))
r = cur.fetchone()
hgb_id = r['id']
print("HGB id:", hgb_id)

# Fix Hemoglobina Cu E
cur.execute("UPDATE rezultate_analize SET denumire_raw = %s, analiza_standard_id = %s WHERE id IN (1729, 1969)",
            ("Hemoglobina", hgb_id))
print("Fix Hemoglobina:", cur.rowcount, "randuri")

# Adauga alias ca sistemul sa retina
cur.execute("INSERT INTO analiza_alias (analiza_standard_id, alias) VALUES (%s, %s) ON CONFLICT (alias) DO NOTHING",
            (hgb_id, "Hemoglobina, Cu E"))
print("Alias 'Hemoglobina, Cu E' adaugat:", cur.rowcount)

conn.commit()

# Verifica final
cur.execute("""
    SELECT b.id, p.nume, COUNT(ra.id) as total,
           SUM(CASE WHEN ra.analiza_standard_id IS NULL THEN 1 ELSE 0 END) as nec
    FROM buletine b JOIN pacienti p ON b.pacient_id = p.id
    LEFT JOIN rezultate_analize ra ON ra.buletin_id = b.id
    GROUP BY b.id, p.nume ORDER BY b.id
""")
print("\n=== Status final buletine ===")
for r in cur.fetchall():
    status = "OK" if not r['nec'] else f"!! {r['nec']} necunoscute"
    print(f"  B{r['id']} {r['nume']} | {r['total']} analize | {status}")

conn.close()
