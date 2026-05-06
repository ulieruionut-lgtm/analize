"""Actualizeaza retroactiv rezultatele Laza care au denumire_raw ce acum se potriveste."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URL", (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
))

def main():
    import psycopg2
    import psycopg2.extras
    from backend.normalizer import _cauta_in_cache

    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT r.id, r.denumire_raw, r.analiza_standard_id
        FROM rezultate_analize r
        JOIN buletine b ON b.id = r.buletin_id
        JOIN pacienti p ON p.id = b.pacient_id
        WHERE (p.nume ILIKE '%Laza%' OR p.prenume ILIKE '%Laza%')
          AND r.analiza_standard_id IS NULL
          AND r.denumire_raw IS NOT NULL
          AND TRIM(r.denumire_raw) != ''
    """)
    rows = cur.fetchall()

    actualizate = 0
    for row in rows:
        aid = _cauta_in_cache(row["denumire_raw"])
        if aid:
            cur.execute(
                "UPDATE rezultate_analize SET analiza_standard_id = %s WHERE id = %s",
                (aid, row["id"]),
            )
            actualizate += 1
            print(f"  + id={row['id']} '{row['denumire_raw'][:45]}...' -> analiza_standard_id={aid}")

    conn.commit()
    print(f"\nActualizate retroactiv: {actualizate} rezultate. Ramase nemapate: {len(rows) - actualizate}")
    conn.close()


if __name__ == "__main__":
    main()
