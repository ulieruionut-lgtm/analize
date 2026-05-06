# -*- coding: utf-8 -*-
"""Curata gunoi OCR din buletinele Vladasel (BOBEICA, ti, Li, spp -, footer etc.)."""
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
import psycopg2.extras

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway",
)

# Denumiri raw care sunt gunoi OCR / footer - de sters
GUNOI_RAW = (
    "ti",
    "Li",
    "Enterococcus spp -",
    "Streptococcus spp -",
    "Staphylococcus spp -",
    "Pseudomonas spp -",
    "Enterobacteriaceae -",
    "Candida spp -",
    "nevoie Candida spp -",
    "micologic, antibiograma,antifungigrama la Streptococ betahemolitic -",
    "doza (0.5 g amoxicillin +",
    "A1 <30: albuminurie normala sau usor",
)

# Prefixe - orice denumire_raw care incepe cu acestea e gunoi
GUNOI_PREFIX = (
    "BOBEICA ",
    "BCBEIEZA ",
    "in 05.01.2026",
    "in 06.01.2026",
    "in 22.12.2025",
)


def _e_gunoi(raw: str) -> bool:
    if not raw or not raw.strip():
        return False
    r = raw.strip()
    if r in GUNOI_RAW:
        return True
    for p in GUNOI_PREFIX:
        if r.startswith(p) or p in r:
            return True
    # "Testele cu marcajul" etc.
    if "Testele cu marcajul" in r or "Aceste rezultate pot fi folosite" in r:
        return True
    return False


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Gaseste rezultatele din buletinele Vladasel care sunt gunoi
    cur.execute("""
        SELECT r.id, r.buletin_id, r.denumire_raw, r.valoare, r.valoare_text
        FROM rezultate_analize r
        JOIN buletine b ON b.id = r.buletin_id
        JOIN pacienti p ON p.id = b.pacient_id
        WHERE (p.nume ILIKE '%%Vladasel%%' OR p.nume ILIKE '%%VLADASEL%%')
    """)
    rows = cur.fetchall()

    de_sters = [r for r in rows if _e_gunoi(r["denumire_raw"])]
    print(f"Buletine Vladasel: {len(rows)} rezultate total")
    print(f"De sters (gunoi): {len(de_sters)}\n")

    for r in de_sters:
        print(f"  DEL id={r['id']} b={r['buletin_id']} raw='{r['denumire_raw'][:55]}...'")
        cur.execute("DELETE FROM rezultate_analize WHERE id = %s", (r["id"],))

    conn.commit()
    print(f"\n✓ Sterse {len(de_sters)} intrari gunoi.")
    conn.close()


if __name__ == "__main__":
    main()
