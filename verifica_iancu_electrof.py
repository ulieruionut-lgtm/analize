import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)

conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Lista toti pacientii
cur.execute("SELECT id, nume, cnp FROM pacienti ORDER BY nume")
pacienti = cur.fetchall()
print("Toti pacientii:")
for p in pacienti:
    print(f"  ID={p['id']} | {p['nume']}")

# Analize nemapate cu 'albumin' sau 'globulin' din toate buletinele
cur.execute("""
    SELECT DISTINCT r.denumire_raw, COUNT(*) as cnt
    FROM rezultate_analize r
    WHERE r.analiza_standard_id IS NULL
      AND r.denumire_raw IS NOT NULL
      AND (LOWER(r.denumire_raw) LIKE '%%albumin%%'
        OR LOWER(r.denumire_raw) LIKE '%%globulin%%'
        OR LOWER(r.denumire_raw) LIKE '%%raport%%'
        OR LOWER(r.denumire_raw) LIKE '%%electrofor%%')
    GROUP BY r.denumire_raw
    ORDER BY cnt DESC
""")
nemapate = cur.fetchall()
print(f"\nAnalize electroforeza/albumina nemapate in tot DB ({len(nemapate)}):")
for r in nemapate:
    print(f"  '{r['denumire_raw']}' (x{r['cnt']})")

# Verifica ce analize de electroforeza exista in analiza_standard
cur.execute("""
    SELECT id, cod_standard, denumire_standard FROM analiza_standard
    WHERE LOWER(denumire_standard) LIKE '%%albumin%%'
       OR LOWER(denumire_standard) LIKE '%%globulin%%'
       OR LOWER(denumire_standard) LIKE '%%electroforez%%'
    ORDER BY denumire_standard
""")
std_electro = cur.fetchall()
print(f"\nAnalize electroforeza in standard ({len(std_electro)}):")
for a in std_electro:
    print(f"  ID={a['id']} | {a['denumire_standard']} | cod={a['cod_standard']}")

conn.close()
