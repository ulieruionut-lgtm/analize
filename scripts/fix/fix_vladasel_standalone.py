# encoding: utf-8
"""
Corecteaza numele pacienților cunoscuti (Vladasel Elena etc.) - script standalone.
Nu depinde de backend - doar de psycopg2 si DATABASE_URL.

Ruleaza pe Railway (cu DATABASE_URL injectat):
  railway run python fix_vladasel_standalone.py

Sau local cu DATABASE_URL setat:
  set DATABASE_URL=postgresql://user:pass@host:port/db
  python fix_vladasel_standalone.py
"""
import os
import sys

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
FIXURI = [
    ("2470112080077", "VLADASEL", "ELENA"),
    ("1461208080072", "VLADASEL", "AUREL-NICOLAE-SORIN"),
    ("2540207080070", "PETREAN", "ANA"),
]


def main():
    if not DATABASE_URL or "sqlite" in DATABASE_URL.lower():
        print("Eroare: Seteaza DATABASE_URL (PostgreSQL) sau ruleaza cu: railway run python fix_vladasel_standalone.py")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("Eroare: pip install psycopg2-binary")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    for cnp, nume, prenume in FIXURI:
        cur.execute("UPDATE pacienti SET nume = %s, prenume = %s WHERE cnp = %s", (nume, prenume, cnp))
        if cur.rowcount:
            print(f"  {cnp}: nume='{nume}' prenume='{prenume}'")
    conn.commit()
    cur.close()
    conn.close()
    print("OK - Nume corectate. Nu se vor mai suprascrie la upload-uri viitoare.")


if __name__ == "__main__":
    main()
