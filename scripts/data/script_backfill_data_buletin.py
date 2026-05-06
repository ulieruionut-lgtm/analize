"""
Backfill pentru buletine vechi: completeaza/normalizeaza data_buletin.

Ce face:
1) Normalizeaza valorile existente in format DD.MM.YYYY (fara ora)
2) Pentru buletine fara data_buletin, incearca sa gaseasca PDF-ul dupa fisier_original
   in directoarele date si extrage data din textul PDF (Data emitere / Data buletin /
   Data recoltare / prima data valida).
3) Optional, daca nu gaseste PDF sau data in PDF, poate folosi fallback din created_at.

Exemple:
  python script_backfill_data_buletin.py --pdf-dir "D:\\PDF-uri" --pdf-dir "C:\\Users\\User\\Downloads"
  python script_backfill_data_buletin.py --pdf-dir "D:\\PDF-uri" --fallback-created-at
  python script_backfill_data_buletin.py --dry-run --fallback-created-at
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parent
DB_DEFAULT = ROOT / "analize.db"
BACKEND_DIR = ROOT / "backend"

# Permite import din backend (pdf_processor + config)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from pdf_processor import extract_text_from_pdf  # type: ignore
except Exception:
    extract_text_from_pdf = None


def normalize_date_text(raw: str) -> Optional[str]:
    """Returneaza DD.MM.YYYY sau None daca nu poate normaliza."""
    if not raw:
        return None
    txt = raw.strip().replace("/", ".").replace("-", ".")

    # DD.MM.YYYY
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", txt)
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"

    # YYYY.MM.DD [optional ora]
    m = re.match(r"^(\d{4})\.(\d{2})\.(\d{2})(?:\s+\d{2}:\d{2}(?::\d{2})?)?$", txt)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"

    # YYYY-MM-DD [optional ora]
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:\s+\d{2}:\d{2}(?::\d{2})?)?$", txt)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"

    # DD.MM.YYYY HH:MM[:SS]
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})\s+\d{2}:\d{2}(?::\d{2})?$", txt)
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"

    # Extrage prima data valida din text
    m = re.search(r"\b(\d{2})[./-](\d{2})[./-](\d{4})\b", txt)
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"

    m = re.search(r"\b(\d{4})[./-](\d{2})[./-](\d{2})\b", txt)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"

    return None


def extract_buletin_date_from_text(text: str) -> Optional[str]:
    """Extrage data buletin din textul PDF."""
    if not text:
        return None

    patterns = [
        r"Data\s+emitere\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+buletin(?:ului)?\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+recoltare\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
        r"Data\s+tiparire\s*[:\-]?\s*(\d{2}[./-]\d{2}[./-]\d{4})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            norm = normalize_date_text(m.group(1))
            if norm:
                return norm
    return None


def build_pdf_index(directories: Iterable[Path]) -> Dict[str, List[Path]]:
    """Index: filename.lower() -> lista path-uri."""
    index: Dict[str, List[Path]] = {}
    for d in directories:
        if not d.exists() or not d.is_dir():
            continue
        for p in d.rglob("*.pdf"):
            key = p.name.lower()
            index.setdefault(key, []).append(p)
    return index


def pick_pdf_candidate(paths: List[Path]) -> Path:
    """Alege PDF-ul cel mai recent modificat."""
    if len(paths) == 1:
        return paths[0]
    return sorted(paths, key=lambda x: x.stat().st_mtime, reverse=True)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill data_buletin pentru analize.db")
    parser.add_argument("--db", default=str(DB_DEFAULT), help="Calea catre baza SQLite (default: analize.db)")
    parser.add_argument("--pdf-dir", action="append", default=[], help="Director unde cauta PDF-uri (poate fi folosit de mai multe ori)")
    parser.add_argument("--all", action="store_true", help="Proceseaza toate buletinele, nu doar cele fara data_buletin")
    parser.add_argument("--fallback-created-at", action="store_true", help="Daca nu poate extrage data din PDF, foloseste data din created_at")
    parser.add_argument("--dry-run", action="store_true", help="Nu scrie in DB, doar afiseaza ce ar schimba")
    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    if not db_path.exists():
        print(f"[EROARE] Baza de date nu exista: {db_path}")
        return 1

    if extract_text_from_pdf is None:
        print("[EROARE] Nu pot importa backend/pdf_processor.py.")
        print("Ruleaza scriptul din folderul proiectului, unde exista backend/ si venv.")
        return 1

    pdf_dirs = [Path(x).resolve() for x in args.pdf_dir]
    pdf_index = build_pdf_index(pdf_dirs) if pdf_dirs else {}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if args.all:
        cur.execute(
            "SELECT id, fisier_original, data_buletin, created_at FROM buletine ORDER BY id"
        )
    else:
        cur.execute(
            "SELECT id, fisier_original, data_buletin, created_at FROM buletine "
            "WHERE data_buletin IS NULL OR TRIM(data_buletin) = '' OR data_buletin LIKE '% %' "
            "ORDER BY id"
        )

    rows = cur.fetchall()
    total = len(rows)
    print(f"Buletine candidate: {total}")
    print(f"PDF dirs indexate: {len(pdf_dirs)} ({sum(len(v) for v in pdf_index.values())} fisiere PDF)")

    updated = 0
    from_pdf = 0
    normalized_existing = 0
    fallback_created = 0
    unresolved = 0

    updates: List[tuple[str, int]] = []

    for r in rows:
        bid = int(r["id"])
        fisier_original = (r["fisier_original"] or "").strip()
        data_buletin = (r["data_buletin"] or "").strip()
        created_at = (r["created_at"] or "").strip()

        # 1) Normalizeaza ce exista deja
        if data_buletin:
            norm = normalize_date_text(data_buletin)
            if norm and norm != data_buletin:
                updates.append((norm, bid))
                normalized_existing += 1
                updated += 1
            continue

        # 2) Incearca extragere din PDF
        new_date: Optional[str] = None
        if fisier_original and pdf_index:
            matches = pdf_index.get(fisier_original.lower(), [])
            if matches:
                candidate = pick_pdf_candidate(matches)
                try:
                    text, _tip, _err = extract_text_from_pdf(str(candidate))
                    new_date = extract_buletin_date_from_text(text)
                    if new_date:
                        from_pdf += 1
                except Exception:
                    new_date = None

        # 3) Fallback optional din created_at
        if not new_date and args.fallback_created_at and created_at:
            new_date = normalize_date_text(created_at)
            if new_date:
                fallback_created += 1

        if new_date:
            updates.append((new_date, bid))
            updated += 1
        else:
            unresolved += 1

    if args.dry_run:
        print("[DRY RUN] Nu scriu in DB.")
        for d, bid in updates[:20]:
            print(f"  ar actualiza buletin #{bid} -> data_buletin={d}")
        if len(updates) > 20:
            print(f"  ... +{len(updates) - 20} alte actualizari")
    else:
        for d, bid in updates:
            cur.execute("UPDATE buletine SET data_buletin = ? WHERE id = ?", (d, bid))
        conn.commit()

    conn.close()

    print("\nRezumat:")
    print(f"  actualizate total: {updated}")
    print(f"  - din PDF: {from_pdf}")
    print(f"  - normalizate existente: {normalized_existing}")
    print(f"  - fallback created_at: {fallback_created}")
    print(f"  fara rezolvare: {unresolved}")
    print("\nGata.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

