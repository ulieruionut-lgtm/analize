"""
Migrează baza de date PostgreSQL (obligatoriu DATABASE_URL).

Rulează: railway run python run_migrations.py
Sau cu .env: asigură-te că DATABASE_URL e setat în .env
"""
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")  # .env în rădăcina proiectului
except ImportError:
    pass

root = Path(__file__).resolve().parent
sql_dir = root / "sql"
url = os.environ.get("DATABASE_URL", "").strip()

if not url or not url.lower().startswith("postgres"):
    print("\nEROARE: Setează DATABASE_URL (PostgreSQL). Rulează cu: railway run python run_migrations.py\n")
    sys.exit(1)

print("Baza de date (PostgreSQL): migrare...")
import psycopg2
conn = psycopg2.connect(url)
conn.autocommit = False
try:
    cur = conn.cursor()
    for fname in ["001_schema.sql", "003_users_auth_postgres.sql", "004_pg_analize_extinse.sql", "005_pg_alias_fix.sql", "006_pg_alias_ocr.sql", "007_ordine_categorie.sql", "008_pg_alias_bioclinica.sql", "009_pg_laboratoare_catalog.sql", "010_pg_alias_laboratoare.sql", "011_pg_valoare_text.sql"]:
        path = sql_dir / fname
        if not path.exists():
            print("Lipsă:", path)
            continue
        sql = path.read_text(encoding="utf-8")
        cur.execute(sql)
        conn.commit()
        print("OK:", fname)
    cur.close()
finally:
    conn.close()
print("Gata. Migrații PostgreSQL finalizate.")
