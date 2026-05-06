"""
Importa laboratoare si catalog analize in baza de date.
Citește: data/laboratoare_surse.json, data/lab_catalogs_collected.json

Ruleaza: python scripts/import_lab_data.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.database import get_cursor, _use_sqlite


def _match_analiza_to_standard(denumire: str, cur, sqlite: bool) -> int | None:
    """Gaseste analiza_standard_id pentru o denumire. Returneaza id sau None."""
    d = denumire.strip()
    if not d or len(d) < 2:
        return None
    d_lower = d.lower()
    # 1. Cauta in analiza_alias (exact)
    if sqlite:
        cur.execute(
            "SELECT analiza_standard_id FROM analiza_alias WHERE LOWER(TRIM(alias)) = ?",
            (d_lower,),
        )
    else:
        cur.execute(
            "SELECT analiza_standard_id FROM analiza_alias WHERE LOWER(TRIM(alias)) = %s",
            (d_lower,),
        )
    row = cur.fetchone()
    if row:
        return row[0] if sqlite else row["analiza_standard_id"]
    # 2. Cauta in analiza_standard.denumire_standard (contains)
    if sqlite:
        cur.execute(
            "SELECT id FROM analiza_standard WHERE LOWER(denumire_standard) LIKE ?",
            (f"%{d_lower}%",),
        )
    else:
        cur.execute(
            "SELECT id FROM analiza_standard WHERE LOWER(denumire_standard) LIKE %s",
            (f"%{d_lower}%",),
        )
    row = cur.fetchone()
    if row:
        return row[0] if sqlite else row["id"]
    # 3. Match direct pe denumire_standard
    if sqlite:
        cur.execute(
            "SELECT id FROM analiza_standard WHERE LOWER(denumire_standard) = ?",
            (d_lower,),
        )
    else:
        cur.execute(
            "SELECT id FROM analiza_standard WHERE LOWER(denumire_standard) = %s",
            (d_lower,),
        )
    row = cur.fetchone()
    if row:
        return row[0] if sqlite else row["id"]
    return None


def upsert_laborator(cur, nume: str, website: str | None, retea: str | None, sqlite: bool) -> int:
    """Insereaza sau gaseste laborator. Returneaza id."""
    if sqlite:
        cur.execute(
            "INSERT OR IGNORE INTO laboratoare (nume, website, retea) VALUES (?, ?, ?)",
            (nume, website or "", retea or nume),
        )
        cur.execute("SELECT id FROM laboratoare WHERE nume = ?", (nume,))
    else:
        cur.execute(
            """INSERT INTO laboratoare (nume, website, retea) VALUES (%s, %s, %s)
               ON CONFLICT (nume) DO NOTHING""",
            (nume, website or "", retea or nume),
        )
        cur.execute("SELECT id FROM laboratoare WHERE nume = %s", (nume,))
    row = cur.fetchone()
    return row[0] if sqlite else row["id"]


def main():
    sqlite = _use_sqlite()
    data_dir = ROOT / "data"
    surse = data_dir / "laboratoare_surse.json"
    catalogs = data_dir / "lab_catalogs_collected.json"

    labs_map = {}
    if surse.exists():
        data = json.loads(surse.read_text(encoding="utf-8"))
        for lab in data.get("laboratoare_nationale", []) + data.get("laboratoare_regionale", []):
            n = lab.get("nume", "").strip()
            if n:
                labs_map[n] = {**lab, "analize": lab.get("analize", [])}

    if catalogs.exists():
        for item in json.loads(catalogs.read_text(encoding="utf-8")):
            n = item.get("laborator", "").strip()
            if n:
                existing = labs_map.get(n, {})
                labs_map[n] = {
                    "nume": n,
                    "website": existing.get("website") or item.get("website", ""),
                    "retea": existing.get("retea", n),
                    "analize": item.get("analize", []) or existing.get("analize", []),
                }

    unique = list(labs_map.values())

    inserted_labs = 0
    inserted_analize = 0
    with get_cursor() as cur:
        for lab in unique:
            nume = lab.get("nume", "").strip()
            if not nume:
                continue
            try:
                lab_id = upsert_laborator(
                    cur,
                    nume,
                    lab.get("website"),
                    lab.get("retea", nume),
                    sqlite,
                )
                inserted_labs += 1
                analize = lab.get("analize", [])
                for den in analize:
                    if not isinstance(den, str):
                        continue
                    aid = _match_analiza_to_standard(den, cur, sqlite)
                    if aid:
                        try:
                            if sqlite:
                                cur.execute(
                                    "INSERT OR IGNORE INTO laborator_analize (laborator_id, analiza_standard_id) VALUES (?, ?)",
                                    (lab_id, aid),
                                )
                            else:
                                cur.execute(
                                    """INSERT INTO laborator_analize (laborator_id, analiza_standard_id)
                                       VALUES (%s, %s) ON CONFLICT (laborator_id, analiza_standard_id) DO NOTHING""",
                                    (lab_id, aid),
                                )
                            inserted_analize += 1
                        except Exception:
                            pass
            except Exception as e:
                print(f"Eroare la {nume}: {e}")

    print(f"Import: {inserted_labs} laboratoare, {inserted_analize} legaturi analize.")


if __name__ == "__main__":
    main()
