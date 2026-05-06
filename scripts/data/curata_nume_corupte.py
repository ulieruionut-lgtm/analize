# encoding: utf-8
"""Curata numele corupte din pacienti (ex: 'Nume pacient: X Medic trimitator:...')."""
import os
import re
import sys
import psycopg2
import psycopg2.extras

sys.stdout.reconfigure(encoding="utf-8")

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway",
)

# Nume corecte pentru pacienti cunoscuti cu date corupte
FIXURI = [
    ("2470112080077", "VLADASEL", "ELENA"),
    ("1461208080072", "VLADASEL", "AUREL-NICOLAE-SORIN"),
    ("2540207080070", "PETREAN", "ANA"),
]


def main():

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Fixuri explicite
    for cnp, nume, prenume in FIXURI:
        cur.execute(
            "UPDATE pacienti SET nume = %s, prenume = %s WHERE cnp = %s",
            (nume, prenume, cnp),
        )
        if cur.rowcount:
            print(f"  {cnp}: nume='{nume}' prenume='{prenume}'")

    # Cauta si alte nume corupte (contin "Medic" sau "Varsta" sau "pacient:")
    cur.execute("""
        SELECT id, cnp, nume, prenume FROM pacienti
        WHERE nume LIKE '%Medic%' OR nume LIKE '%Varsta%' OR nume LIKE '%pacient%'
           OR nume LIKE '%Nume pacient%' OR LENGTH(nume) > 80
    """)
    suspecte = cur.fetchall()
    if suspecte:
        print("\nAlte inregistrari suspecte (verifica manual):")
        for r in suspecte:
            print(f"  id={r['id']} cnp={r['cnp']} nume={repr(r['nume'])[:80]}...")

    conn.commit()
    print("\nOK - nume curatate.")
    conn.close()


if __name__ == "__main__":
    main()
