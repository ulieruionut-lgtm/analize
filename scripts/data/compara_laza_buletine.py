# -*- coding: utf-8 -*-
"""Compara rezultatele din buletinele Laza - identifica diferente intre upload-uri."""
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

    # Buletine Laza: 42 (05.12), 45 si 46 (22.12 - cele 2 fisiere identice)
    cur.execute("""
        SELECT r.id, r.buletin_id, r.denumire_raw, r.analiza_standard_id,
               r.valoare, r.valoare_text, r.unitate, a.denumire_standard, a.cod_standard
        FROM rezultate_analize r
        LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
        JOIN buletine b ON b.id = r.buletin_id
        JOIN pacienti p ON p.id = b.pacient_id
        WHERE p.nume ILIKE '%%Laza%%'
        ORDER BY r.buletin_id, r.ordine NULLS LAST, r.id
    """)
    rows = cur.fetchall()

    # Grupeaza pe buletin
    by_buletin = {}
    for r in rows:
        bid = r["buletin_id"]
        if bid not in by_buletin:
            by_buletin[bid] = []
        by_buletin[bid].append(r)

    # Info buletine
    cur.execute("""
        SELECT b.id, b.data_buletin, b.fisier_original
        FROM buletine b
        JOIN pacienti p ON p.id = b.pacient_id
        WHERE p.nume ILIKE '%%Laza%%'
        ORDER BY b.data_buletin, b.id
    """)
    buletine_info = {b["id"]: b for b in cur.fetchall()}

    print("=== BULETINE LAZA ===\n")
    for bid in sorted(by_buletin.keys()):
        info = buletine_info.get(bid, {})
        print(f"Buletin {bid}: {info.get('data_buletin')} - {info.get('fisier_original')}")
        print(f"  Total analize: {len(by_buletin[bid])}")
        for i, r in enumerate(by_buletin[bid][:25]):
            v = r["valoare"] if r["valoare"] is not None else (r["valoare_text"] or "-")
            std = r["denumire_standard"] or r["denumire_raw"]
            print(f"    {i+1}. {std} = {v} {r['unitate'] or ''}")
        if len(by_buletin[bid]) > 25:
            print(f"    ... +{len(by_buletin[bid])-25} mai multe")
        print()

    # Compara B45 vs B46 (cele 2 din 22.12 - ar trebui sa fie identice)
    b45 = {(r["denumire_standard"] or r["denumire_raw"]): r for r in by_buletin.get(45, [])}
    b46 = {(r["denumire_standard"] or r["denumire_raw"]): r for r in by_buletin.get(46, [])}

    print("=== COMPARATIE B45 vs B46 (ambele 22.12.2025) ===\n")

    toate = set(b45.keys()) | set(b46.keys())
    diferente = []
    for nume in sorted(toate):
        r45 = b45.get(nume)
        r46 = b46.get(nume)
        v45 = (r45["valoare"] if r45 and r45["valoare"] is not None else r45["valoare_text"]) if r45 else None
        v46 = (r46["valoare"] if r46 and r46["valoare"] is not None else r46["valoare_text"]) if r46 else None
        if r45 is None:
            diferente.append((nume, "LIPSESTE in B45", v46))
        elif r46 is None:
            diferente.append((nume, "LIPSESTE in B46", v45))
        elif v45 != v46:
            diferente.append((nume, f"VALORI DIFERITE: B45={v45} vs B46={v46}", None))

    if diferente:
        print(f"Gasite {len(diferente)} diferente:\n")
        for nume, desc, v in diferente:
            print(f"  - {nume}: {desc}")
    else:
        print("Nicio diferenta - B45 si B46 sunt identice.")

    # Verifica si denumiri raw diferite pentru aceeasi analiza
    print("\n=== DENUMIRI RAW DIFERITE (aceeasi analiza, nume diferit in PDF) ===\n")
    raw_by_std = {}
    for bid, lista in by_buletin.items():
        for r in lista:
            std = r["denumire_standard"] or r["denumire_raw"]
            raw = r["denumire_raw"] or ""
            if std not in raw_by_std:
                raw_by_std[std] = set()
            raw_by_std[std].add((raw, bid))
    for std, raws in sorted(raw_by_std.items()):
        if len(set(r for r, _ in raws)) > 1:
            print(f"  {std}:")
            for raw, bid in raws:
                print(f"    B{bid}: '{raw}'")

    conn.close()
    print("\n=== GATA ===")


if __name__ == "__main__":
    main()
