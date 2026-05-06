# -*- coding: utf-8 -*-
"""
Corectează numele pacienților EXISTENȚI în baza de date.
Rulează acest script pentru a repara datele deja salvate - nu e nevoie să aștepți redeploy.

Utilizare:
  venv\\Scripts\\python.exe fix_nume_pacienti_existenti.py
  venv\\Scripts\\python.exe fix_nume_pacienti_existenti.py --dry-run   # doar afișează ce s-ar schimba
  # sau pe Railway: railway run python fix_nume_pacienti_existenti.py

Folosește DATABASE_URL din .env (PostgreSQL Railway sau SQLite local).
"""
import argparse
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from backend.database import get_cursor, _use_sqlite, _row_get
from backend.parser import _curata_nume, _nume_este_gunoi

# CNP -> (nume, prenume) corect
_PACIENTI_CUNOSCUTI = {
    "2470112080077": ("VLADASEL", "ELENA"),
    "1461208080072": ("VLADASEL", "AUREL-NICOLAE-SORIN"),
    "2540207080070": ("PETREAN", "ANA"),
    "1420917080026": ("IANCU", "GHEORGHE"),
    "2970424080038": ("MANDACHE", "OANA ALEXANDRA"),
    "5240222080031": ("NITU", "MATEI"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Afișează ce s-ar schimba, fără actualizare")
    args = parser.parse_args()
    dry_run = args.dry_run

    with get_cursor(commit=False) as cur:
        cur.execute("SELECT id, cnp, nume, prenume FROM pacienti")
        rows = cur.fetchall()

    updates = []
    for row in rows:
        rid = _row_get(row, "id") or _row_get(row, 0)
        cnp = (_row_get(row, "cnp") or _row_get(row, 1)) or ""
        nume_raw = _row_get(row, "nume") or _row_get(row, 2) or ""
        prenume_raw = _row_get(row, "prenume") or _row_get(row, 3) or ""

        # Combinam pentru curatare, apoi impartim
        full_raw = f"{nume_raw} {prenume_raw}".strip()
        full_curat = _curata_nume(full_raw)

        if _nume_este_gunoi(full_curat):
            nume_nou, prenume_nou = "Necunoscut", None
        elif cnp in _PACIENTI_CUNOSCUTI:
            nume_nou, prenume_nou = _PACIENTI_CUNOSCUTI[cnp]
        elif full_curat and full_curat != "Necunoscut":
            parts = full_curat.split(None, 1)
            nume_nou = parts[0] if parts else "Necunoscut"
            prenume_nou = parts[1] if len(parts) >= 2 else None
        else:
            continue

        if (nume_nou, prenume_nou or "") != (nume_raw, prenume_raw or ""):
            updates.append((rid, nume_nou, prenume_nou, nume_raw, prenume_raw))

    if not updates:
        print("Niciun nume de corectat. Datele sunt OK.")
        return

    print(f"Se actualizează {len(updates)} pacienți:\n")
    for rid, nume_nou, prenume_nou, nume_vechi, prenume_vechi in updates:
        vechi = f"{nume_vechi} {prenume_vechi or ''}".strip()
        nou = f"{nume_nou} {prenume_nou or ''}".strip()
        suf = "..." if len(vechi) > 55 else ""
        print(f"  {vechi[:55]}{suf}")
        print(f"    -> {nou}")

    if dry_run:
        print(f"\n[DRY-RUN] Rulează fără --dry-run pentru a aplica cele {len(updates)} modificări.")
        return

    with get_cursor() as cur:
        ph = "?" if _use_sqlite() else "%s"
        for rid, nume_nou, prenume_nou, _, _ in updates:
            cur.execute(
                f"UPDATE pacienti SET nume = {ph}, prenume = {ph} WHERE id = {ph}",
                (nume_nou, prenume_nou, rid),
            )

    print(f"\n✓ Actualizat {len(updates)} pacienți. Reîncarcă pagina (F5) pentru a vedea modificările.")


if __name__ == "__main__":
    main()
