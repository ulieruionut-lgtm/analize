# -*- coding: utf-8 -*-
"""Adauga Flora microbiana (sediment urinar) - analiza standard + alias pentru Vladasel."""
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
import psycopg2.extras

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway",
)

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Creeaza FLORA_URINA daca nu exista
    cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'FLORA_URINA'")
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES ('FLORA_URINA', 'Flora microbiana (sediment urinar)')",
        )
        cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'FLORA_URINA'")
        std_id = cur.fetchone()["id"]
        print(f"  + analiza_standard: FLORA_URINA (id={std_id})")
    else:
        std_id = row["id"]

    # Adauga alias
    for alias in ["Flora microbiana", "Flora microbiana urina", "1.2.12 Flora microbiana"]:
        try:
            cur.execute(
                "INSERT INTO analiza_alias (analiza_standard_id, alias) VALUES (%s, %s) ON CONFLICT (alias) DO NOTHING",
                (std_id, alias),
            )
            if cur.rowcount > 0:
                print(f"  + alias: '{alias}'")
        except Exception as e:
            print(f"  ERR '{alias}': {e}")

    conn.commit()

    # Actualizeaza rezultatele Vladasel care au "Flora microbiana"
    cur.execute("""
        UPDATE rezultate_analize r
        SET analiza_standard_id = %s
        FROM buletine b, pacienti p
        WHERE r.buletin_id = b.id AND b.pacient_id = p.id
          AND p.nume ILIKE '%%Vladasel%%'
          AND r.analiza_standard_id IS NULL
          AND (LOWER(r.denumire_raw) LIKE '%%flora microbiana%%' OR r.denumire_raw = 'Alte')
    """, (std_id,))
    # Nu mapam "Alte" la FLORA - "Alte" e prea generic. Doar Flora microbiana.
    cur.execute("""
        UPDATE rezultate_analize r
        SET analiza_standard_id = NULL
        FROM buletine b, pacienti p
        WHERE r.buletin_id = b.id AND b.pacient_id = p.id
          AND p.nume ILIKE '%%Vladasel%%'
          AND r.denumire_raw = 'Alte'
    """)
    # Refac doar Flora
    cur.execute("""
        UPDATE rezultate_analize r
        SET analiza_standard_id = %s
        FROM buletine b, pacienti p
        WHERE r.buletin_id = b.id AND b.pacient_id = p.id
          AND p.nume ILIKE '%%Vladasel%%'
          AND r.analiza_standard_id IS NULL
          AND LOWER(r.denumire_raw) LIKE '%%flora microbiana%%'
    """, (std_id,))
    n = cur.rowcount
    conn.commit()
    print(f"\n  Actualizate retroactiv: {n} rezultate 'Flora microbiana'")

    conn.close()
    print("\n=== GATA ===")


if __name__ == "__main__":
    main()
