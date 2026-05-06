# -*- coding: utf-8 -*-
"""
Curățare unificată gunoi – aceleași reguli ca ``backend.parser.este_denumire_gunoi``
și ca normalizer-ul (care acum NU mai adaugă gunoi în analiza_necunoscuta).

Problema veche: orice denumire nerecunoscută era logată în „Analize necunoscute”,
chiar dacă era nume/adresă/notă OCR. Scripturile anterioare (ex.
``curatare_analize_necunoscute_gunoi.py``) foloseau doar regulile din parser,
dar fără filtru la upload gunoiul se acumula din nou.

Acum:
1. Upload: ``normalize_rezultat`` sare peste ``_log_necunoscuta`` dacă e gunoi.
2. Acest script: șterge rândurile deja existente care încă îndeplinesc criteriile.

Utilizare:
  python curatare_gunoi_pipeline.py                    # simulare (implicit)
  python curatare_gunoi_pipeline.py --exec             # șterge din analiza_necunoscuta (doar neaprobate)
  python curatare_gunoi_pipeline.py --exec --rezultate
        # + șterge din rezultate_analize rândurile NEMAPATE care sunt gunoi (curăță buletinele)

  python curatare_gunoi_pipeline.py --exec --include-aprobate
        # rare: șterge gunoi și din rânduri aprobate în analiza_necunoscuta (atenție)

Necesită .env / DATABASE_URL corect.

Recomandat pe Windows: ``venv\\Scripts\\python.exe curatare_gunoi_pipeline.py ...``
(dacă nu ai venv, instalare: ``python -m venv venv`` apoi ``pip install -r requirements.txt``).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Permite ``import reexec_cu_venv`` indiferent de directorul curent
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
    ap = argparse.ArgumentParser(description="Curățare gunoi (analize necunoscute + opțional rezultate)")
    ap.add_argument("--exec", action="store_true", help="Execută ștergerea (altfel simulare)")
    ap.add_argument(
        "--rezultate",
        action="store_true",
        help="Șterge și din rezultate_analize (doar analiza_standard_id IS NULL + gunoi)",
    )
    ap.add_argument(
        "--include-aprobate",
        action="store_true",
        help="Include rânduri aprobate în analiza_necunoscuta (implicit doar neaprobate)",
    )
    ap.add_argument("--json", action="store_true", help="Ieșire JSON")
    ns = ap.parse_args()

    try:
        from backend.database import curata_gunoi_analize_pipeline
    except ModuleNotFoundError as e:
        print(mesaj_lipsa_dependente(getattr(e, "name", "necunoscut"), __file__), file=sys.stderr)
        return 1

    dry_run = not ns.exec
    stats = curata_gunoi_analize_pipeline(
        dry_run=dry_run,
        sterge_rezultate_nemapate=ns.rezultate,
        doar_neaprobate_necunoscute=not ns.include_aprobate,
    )

    if ns.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    print("=== Curățare gunoi (reguli = este_denumire_gunoi din parser) ===\n")
    print("Mod:", "SIMULARE" if dry_run else "EXECUTAT")
    print("Analize necunoscute scanate:", stats["necunoscute_scanate"])
    print("Analize necunoscute de șters (gunoi):", stats["necunoscute_sterse"])
    if ns.rezultate:
        print("Rezultate nemapate scanate:", stats["rezultate_scanate"])
        print("Rezultate gunoi de șters:", stats["rezultate_sterse"])
    if stats.get("exemple_necunoscute"):
        print("\nExemple (necunoscute):")
        for x in stats["exemple_necunoscute"][:15]:
            print(f"  id={x['id']} | {x['denumire_raw']!r}")
    if ns.rezultate and stats.get("exemple_rezultate"):
        print("\nExemple (rezultate):")
        for x in stats["exemple_rezultate"][:15]:
            print(f"  id={x['id']} | {x['denumire_raw']!r}")
    if dry_run and (stats["necunoscute_sterse"] or stats.get("rezultate_sterse")):
        print("\n→ Rulează cu --exec pentru a aplica ștergerea.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
