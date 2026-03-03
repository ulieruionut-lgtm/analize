import psycopg2, os
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
cur.execute("SELECT cod_standard, denumire_standard FROM analiza_standard WHERE denumire_standard ILIKE '%vitamina%' OR cod_standard ILIKE '%vit%' ORDER BY cod_standard")
for r in cur.fetchall():
    print(r)
conn.close()
