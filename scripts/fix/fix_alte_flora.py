# -*- coding: utf-8 -*-
"""Mapeaza 'Alte' (cristale) si 'Flora microbiana' la analize standard."""
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

    # CRISTALE_URINA pentru "Alte" (context sediment - "Alte cristale")
    cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'CRISTALE_URINA'")
    cristale_id = cur.fetchone()
    if cristale_id:
        cur.execute("""
            UPDATE rezultate_analize r
            SET analiza_standard_id = %s
            FROM buletine b, pacienti p
            WHERE r.buletin_id = b.id AND b.pacient_id = p.id
              AND (p.nume ILIKE '%%Vladasel%%')
              AND r.analiza_standard_id IS NULL
              AND (LOWER(TRIM(r.denumire_raw)) = 'alte'
                   OR r.denumire_raw ILIKE '%%alte cristale%%')
        """, (cristale_id["id"],))
        n = cur.rowcount
        if n:
            print(f"  Mapat 'Alte' -> CRISTALE_URINA: {n} rezultate")

    # FLORA_URINA pentru "Flora microbiana"
    cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'FLORA_URINA'")
    flora_id = cur.fetchone()
    if flora_id:
        cur.execute("""
            UPDATE rezultate_analize r
            SET analiza_standard_id = %s
            FROM buletine b, pacienti p
            WHERE r.buletin_id = b.id AND b.pacient_id = p.id
              AND (p.nume ILIKE '%%Vladasel%%')
              AND r.analiza_standard_id IS NULL
              AND (LOWER(TRIM(r.denumire_raw)) LIKE '%%flora microbiana%%')
        """, (flora_id["id"],))
        n = cur.rowcount
        if n:
            print(f"  Mapat 'Flora microbiana' -> FLORA_URINA: {n} rezultate")

    conn.commit()
    print("\nGata.")
    conn.close()

if __name__ == "__main__":
    main()
