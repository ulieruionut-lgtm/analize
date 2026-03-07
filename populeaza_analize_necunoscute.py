"""
Populează analiza_necunoscuta din rezultatele nemapate existente în rezultate_analize.

Rulează acest script când rubrica "Analize necunoscute" este goală dar există
rezultate cu analiza_standard_id IS NULL - de ex. dacă _log_necunoscuta a eșuat
la upload sau date au fost importate altfel.

Utilizare: python populeaza_analize_necunoscute.py
"""
import os
import sys
import psycopg2
import psycopg2.extras

sys.stdout.reconfigure(encoding="utf-8")

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway",
)

# Denumiri evidente de ignorat (gunoi OCR, fragmente)
GUNOI_PATTERNS = (
    "Pg.",
    "eGFR:",
    "k =",
    "crescute ≥",
    "Interpretare",
    "Absenti Absenti",
    "Absente Absente",
    "Galbendeschis",
    "Foarterare",
    "esantion",
    "metoda",
    "spectrofotometrie",
)


def _e_gunoi(raw: str) -> bool:
    if not raw or len(raw.strip()) < 3:
        return True
    r = raw.strip().lower()
    for p in GUNOI_PATTERNS:
        if p.lower() in r:
            return True
    return False


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 1. Numără nemapate înainte
    cur.execute(
        """
        SELECT denumire_raw, COUNT(*) as cnt
        FROM rezultate_analize
        WHERE analiza_standard_id IS NULL
          AND denumire_raw IS NOT NULL
          AND TRIM(denumire_raw) != ''
        GROUP BY denumire_raw
        ORDER BY cnt DESC
        """
    )
    rows = cur.fetchall()

    # 2. Filtrează gunoiul
    de_adaugat = [(r["denumire_raw"], r["cnt"]) for r in rows if not _e_gunoi(r["denumire_raw"])]

    if not de_adaugat:
        print("Nicio analiză nemapată de adăugat în analiza_necunoscuta.")
        if rows:
            print(f"  ({len(rows)} intrări ignorate ca gunoi OCR)")
        conn.close()
        return

    print(f"Găsite {len(de_adaugat)} denumiri nemapate de adăugat în analiza_necunoscuta:\n")

    adaugate = 0
    for raw, cnt in de_adaugat:
        try:
            cur.execute(
                """
                INSERT INTO analiza_necunoscuta (denumire_raw, aparitii)
                VALUES (%s, %s)
                ON CONFLICT (denumire_raw) DO UPDATE SET
                    aparitii = analiza_necunoscuta.aparitii + EXCLUDED.aparitii,
                    updated_at = NOW()
                """,
                (raw.strip(), cnt),
            )
            adaugate += 1
            print(f"  + '{raw[:60]}{'...' if len(raw) > 60 else ''}' ({cnt} apariții)")
        except Exception as e:
            print(f"  ERR '{raw[:40]}': {e}")

    conn.commit()

    cur.execute("SELECT COUNT(*) as n FROM analiza_necunoscuta WHERE aprobata = 0")
    total_nec = cur.fetchone()["n"]

    print(f"\n✓ Adăugate/actualizate: {adaugate} intrări")
    print(f"✓ Total analize necunoscute (neaprobate): {total_nec}")
    print("\nDeschide aplicația → tab 'Analize necunoscute' pentru a le asocia sau șterge.")

    conn.close()


if __name__ == "__main__":
    main()
