import psycopg2, psycopg2.extras, sys
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='analiza_standard' ORDER BY ordinal_position")
cols = [r['column_name'] for r in cur.fetchall()]
print("Coloane analiza_standard:", cols)

cur.execute("SELECT * FROM analiza_standard ORDER BY denumire_standard LIMIT 5")
rows = cur.fetchall()
print("\nExemplu randuri:")
for r in rows:
    print(dict(r))

# Cauta calciu
cur.execute("SELECT * FROM analiza_standard WHERE denumire_standard ILIKE '%calciu%' OR cod_standard ILIKE '%calciu%' OR cod_standard ILIKE '%CA%'")
rows = cur.fetchall()
print("\nAnalize cu 'calciu':")
for r in rows:
    print(f"  ID={r['id']} | {r['denumire_standard']} | cod={r['cod_standard']}")
conn.close()
