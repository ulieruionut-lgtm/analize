import psycopg2, os
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# Corecteaza MPV in buletin 14
cur.execute("""
    UPDATE rezultate_analize
    SET valoare=9.9, unitate='fL', flag=NULL
    WHERE buletin_id=14
      AND (denumire_raw ILIKE '%%MPV%%' OR denumire_raw ILIKE '%%plachetar%%' OR denumire_raw ILIKE '%%siehetie%%')
      AND valoare > 30
""")
print(f"MPV corectat: {cur.rowcount} randuri")
conn.commit()
conn.close()
