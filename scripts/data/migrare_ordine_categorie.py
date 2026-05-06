"""
Migrare: adauga coloanele 'ordine' si 'categorie' in tabela rezultate_analize.
Ruleaza o singura data pe Railway.
"""
import sys, psycopg2
sys.stdout.reconfigure(encoding="utf-8")
DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Verifica daca coloanele exista deja
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name='rezultate_analize' AND column_name IN ('ordine','categorie')
""")
existente = {r[0] for r in cur.fetchall()}

if 'ordine' not in existente:
    cur.execute("ALTER TABLE rezultate_analize ADD COLUMN ordine INTEGER DEFAULT NULL")
    print("Adaugat coloana: ordine")
else:
    print("ordine exista deja")

if 'categorie' not in existente:
    cur.execute("ALTER TABLE rezultate_analize ADD COLUMN categorie VARCHAR(100) DEFAULT NULL")
    print("Adaugat coloana: categorie")
else:
    print("categorie exista deja")

cur.execute("CREATE INDEX IF NOT EXISTS idx_rezultate_ordine ON rezultate_analize(buletin_id, ordine)")
print("Index creat/verificat")

conn.commit()
conn.close()
print("OK - migrare finalizata")
