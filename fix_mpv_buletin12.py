"""Corecteaza MPV in buletin_id=12 (OCR a citit 9.9 fL ca 99.0 f..)"""
import psycopg2, os
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
cur.execute("""
    UPDATE rezultate_analize
    SET valoare=9.9, unitate='fL', flag=NULL
    WHERE denumire_raw='Volumul mediu plachetar (MPV)'
      AND buletin_id=12
""")
print(f"MPV corectat: {cur.rowcount} randuri actualizate")
conn.commit()
conn.close()
