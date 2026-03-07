import psycopg2, psycopg2.extras

DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Verifica ultimele aliasuri adaugate
print("=== Ultimele aliasuri adaugate (max 20) ===")
cur.execute("""
    SELECT aa.id, aa.alias, aa.analiza_standard_id, ast.cod_standard, ast.denumire_standard
    FROM analiza_alias aa
    JOIN analiza_standard ast ON ast.id = aa.analiza_standard_id
    ORDER BY aa.id DESC
    LIMIT 20
""")
for row in cur.fetchall():
    print(f"  id={row['id']} | alias='{row['alias']}' -> {row['cod_standard']} ({row['denumire_standard']})")

# Verifica analize_necunoscuta recente
print("\n=== Analize necunoscute recente (ultimele 10) ===")
cur.execute("""
    SELECT id, denumire_raw, aparitii, aprobata, analiza_standard_id, updated_at
    FROM analiza_necunoscuta
    ORDER BY updated_at DESC
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  id={row['id']} | '{row['denumire_raw']}' | aparitii={row['aparitii']} | aprobata={row['aprobata']} | std_id={row['analiza_standard_id']} | {str(row['updated_at'])[:19]}")

# Cauta specific Hemoglobina
print("\n=== Cauta 'hemoglobin' in aliasuri ===")
cur.execute("""
    SELECT aa.alias, aa.analiza_standard_id, ast.cod_standard, ast.denumire_standard
    FROM analiza_alias aa
    JOIN analiza_standard ast ON ast.id = aa.analiza_standard_id
    WHERE LOWER(aa.alias) LIKE '%%hemoglobin%%'
    ORDER BY aa.id
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  '{row['alias']}' -> {row['cod_standard']} ({row['denumire_standard']})")
else:
    print("  Nu exista niciun alias cu 'hemoglobin'")

# Cauta hemoglobina in rezultate recente
print("\n=== Ultimele rezultate adaugate pentru Laza (buletin 20) ===")
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.analiza_standard_id, ast.cod_standard, r.created_at
    FROM rezultate_analize r
    LEFT JOIN analiza_standard ast ON ast.id = r.analiza_standard_id
    WHERE r.buletin_id = 20
    ORDER BY r.created_at DESC
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  rid={row['id']} | '{row['denumire_raw']}' = {row['valoare']} | std={row['cod_standard']} | {str(row['created_at'])[:19]}")

conn.close()
