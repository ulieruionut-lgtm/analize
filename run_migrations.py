"""
Rulare migrari baza de date (SQLite sau PostgreSQL).

Utilizeaza sistemul de versioning cu tabela schema_migrations:
- Fiecare fisier SQL din /sql/ este aplicat o singura data
- Versiunile aplicate sunt inregistrate in schema_migrations
- Fisierele deja aplicate sunt sarite automat

Utilizare:
    python run_migrations.py                    # detecteaza DB din DATABASE_URL / .env
    railway run python run_migrations.py        # pe Railway cu PostgreSQL
"""
import sys
from pathlib import Path

# Incarca .env daca exista (pentru DATABASE_URL)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# Adauga directorul radacina la PYTHONPATH pentru importuri
import os
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.migration_runner import aplica_migrari

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    print("Rulare migrari baza de date...\n")
    result = aplica_migrari(verbose=True)

    print(f"\n{'='*50}")
    print(f"Aplicate:  {len(result['aplicate'])} fisiere")
    print(f"Sarite:    {len(result['sarite'])} (deja aplicate)")
    print(f"Erori:     {len(result['erori'])}")
    if result["erori"]:
        print("Detalii erori:")
        for err in result["erori"]:
            print(f"  - {err}")
    print(f"{'='*50}")
    print(f"Status: {'OK' if result['ok'] else 'EROARE'}")

    sys.exit(0 if result["ok"] else 1)
