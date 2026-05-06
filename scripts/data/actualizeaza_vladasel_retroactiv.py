# -*- coding: utf-8 -*-
"""Actualizeaza retroactiv rezultatele nemapate ale Vladasel folosind aliasurile noi."""
import os
import re
import sys
sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
import psycopg2.extras

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway",
)


def strip_regina_maria_prefix(raw: str) -> str:
    """Elimina prefix numeric Regina Maria: 1.1.4, 1.2.4, 1:2, 1-3, $.1.11, 11,13 etc."""
    s = raw.strip()
    # Pattern: N.N.N sau N:N sau N-N sau $.N.N sau N,N.N la inceput
    m = re.match(r"^(\d+[.,:\-]\d+([.,:\-]\d+)*|\$\.\d+\.\d+)\s*\*?\s*", s)
    if m:
        return s[m.end() :].strip()
    return s


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Rezultate nemapate din buletinele Vladasel (49, 50)
    cur.execute("""
        SELECT r.id, r.denumire_raw
        FROM rezultate_analize r
        JOIN buletine b ON b.id = r.buletin_id
        JOIN pacienti p ON p.id = b.pacient_id
        WHERE p.nume ILIKE '%%Vladasel%%'
          AND r.analiza_standard_id IS NULL
          AND r.denumire_raw IS NOT NULL
          AND TRIM(r.denumire_raw) != ''
    """)
    rows = cur.fetchall()

    # Incarca aliasuri: LOWER(alias) -> analiza_standard_id
    cur.execute("SELECT LOWER(TRIM(alias)) as k, analiza_standard_id FROM analiza_alias")
    alias_map = {r["k"]: r["analiza_standard_id"] for r in cur.fetchall()}

    actualizate = 0
    for r in rows:
        raw = r["denumire_raw"] or ""
        raw_trim = raw.strip()
        raw_lower = raw_trim.lower()

        aid = None
        # 1. Match exact
        if raw_lower in alias_map:
            aid = alias_map[raw_lower]
        # 2. Match dupa strip prefix
        if aid is None:
            stripped = strip_regina_maria_prefix(raw_trim)
            if stripped and stripped.lower() in alias_map:
                aid = alias_map[stripped.lower()]

        if aid is not None:
            cur.execute(
                "UPDATE rezultate_analize SET analiza_standard_id = %s WHERE id = %s",
                (aid, r["id"]),
            )
            actualizate += 1
            print(f"  OK id={r['id']}: '{raw_trim[:50]}...' -> std_id={aid}")

    conn.commit()
    print(f"\n=== GATA: {actualizate} rezultate actualizate din {len(rows)} nemapate ===")
    conn.close()


if __name__ == "__main__":
    main()
