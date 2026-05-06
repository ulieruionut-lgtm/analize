# -*- coding: utf-8 -*-
"""
Completează retroactiv coloana categorie pe analiza_necunoscuta, din rezultate_analize
(aceeași denumire_raw → secțiunea salvată la upload).

Mod simulare (implicit):
  python completeaza_categorie_necunoscute.py
  venv\\Scripts\\python.exe completeaza_categorie_necunoscute.py

Aplică în baza de date:
  python completeaza_categorie_necunoscute.py --exec

Opțional, primele N rânduri (test):
  python completeaza_categorie_necunoscute.py --limit 10 --exec

Asigură-te că .env / DATABASE_URL indică baza corectă (SQLite local sau PostgreSQL).

API (doar cont admin): POST /api/admin/backfill-necunoscuta-categorie
  Body JSON: {"dry_run": true|false, "limit": null|int}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from reexec_cu_venv import mesaj_lipsa_dependente, reexec_cu_venv_if_needed

reexec_cu_venv_if_needed(__file__)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill categorie pentru analiza_necunoscuta")
    parser.add_argument(
        "--exec",
        action="store_true",
        help="Scrie în baza de date (fără acest flag = doar simulare).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maxim rânduri din analiza_necunoscuta fără categorie de examinat.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Afișează rezultatul ca JSON (fără text uman).",
    )
    args = parser.parse_args()

    try:
        from backend.database import backfill_categorie_necunoscuta_din_rezultate
    except ModuleNotFoundError as e:
        print(mesaj_lipsa_dependente(getattr(e, "name", "necunoscut"), __file__), file=sys.stderr)
        return 1

    dry_run = not args.exec
    stats = backfill_categorie_necunoscuta_din_rezultate(dry_run=dry_run, limit=args.limit)

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    print("=== Completează categorie (analiza_necunoscuta ← rezultate_analize) ===\n")
    print(f"Mod: {'SIMULARE (nu s-a scris nimic)' if dry_run else 'EXECUTAT — modificări salvate'}")
    print(f"Examinat rânduri necunoscute fără categorie: {stats['examinat']}")
    print(f"Cu categorie găsită în rezultate:          {stats['cu_categorie_gasita']}")
    print(f"Fără categorie în rezultate (sărit):      {stats['fara_categorie_in_rezultate']}")
    if dry_run:
        print(f"Ar fi actualizate:                         {stats['actualizate']}")
    else:
        print(f"Actualizate în DB:                       {stats['actualizate']}")

    if stats.get("esantion"):
        print("\nEșantion:")
        for row in stats["esantion"]:
            print(f"  id={row['id']} | {row['categorie']!r} ← {row['denumire_raw']!r}")

    if dry_run and stats["cu_categorie_gasita"]:
        print("\n→ Rulează cu --exec pentru a salva în baza de date.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
