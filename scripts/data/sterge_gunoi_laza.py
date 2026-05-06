import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)

conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Gunoi identificat - raw-uri care nu sunt analize reale
gunoi = ['14.2', 'Coad:5hn a', 'E Cod:5', 'i a ( )', 'IRT aa cn aia aaa a ES A E NENEA a']

print("Sterg inregistrari gunoi din buletinele Laza:")
for g in gunoi:
    cur.execute(
        "SELECT r.id, b.data_buletin FROM rezultate_analize r "
        "JOIN buletine b ON b.id = r.buletin_id "
        "JOIN pacienti p ON p.id = b.pacient_id "
        "WHERE p.nume ILIKE '%%Laza%%' AND r.denumire_raw = %s",
        (g,)
    )
    rows = cur.fetchall()
    for row in rows:
        cur.execute("DELETE FROM rezultate_analize WHERE id = %s", (row['id'],))
        print(f"  STERS: '{g}' (RID={row['id']}, buletin {row['data_buletin'].date()})")

conn.commit()
print("\nGata!")

# Verifica starea finala
cur.execute("""
    SELECT DISTINCT r.denumire_raw
    FROM rezultate_analize r
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE p.nume ILIKE '%%Laza%%'
      AND r.analiza_standard_id IS NULL
      AND r.denumire_raw IS NOT NULL AND r.denumire_raw != ''
""")
ramate = cur.fetchall()
if ramate:
    print(f"Inca nemapate ({len(ramate)}): {[r['denumire_raw'] for r in ramate]}")
else:
    print("Toate analizele Laza sunt acum curate si mapate!")

conn.close()
