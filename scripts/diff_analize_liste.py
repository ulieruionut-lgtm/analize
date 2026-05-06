#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compară două liste de analize (câte o denumire pe linie).
Utilizare:
  python scripts/diff_analize_liste.py din_pdf.txt din_app.txt

Opțional: normalizează diacritice/spații pentru potrivire mai laxă:
  python scripts/diff_analize_liste.py a.txt b.txt --fuzzy
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _norm(s: str, fuzzy: bool) -> str:
    s = s.strip().lower()
    if not fuzzy:
        return s
    s = (
        s.replace("ș", "s")
        .replace("ş", "s")
        .replace("ț", "t")
        .replace("ă", "a")
        .replace("â", "a")
        .replace("î", "i")
    )
    s = re.sub(r"\s+", " ", s)
    return s


def _load(p: Path) -> list[str]:
    if not p.is_file():
        print("Lipsește fișierul:", p, file=sys.stderr)
        sys.exit(1)
    lines = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Diff două liste de analize")
    ap.add_argument("fisier_pdf", type=Path, help="Listă referință (ex. din buletin)")
    ap.add_argument("fisier_app", type=Path, help="Listă din aplicație")
    ap.add_argument("--fuzzy", action="store_true", help="Potrivire aproximativă (fără diacritice)")
    args = ap.parse_args()

    a = _load(args.fisier_pdf)
    b = _load(args.fisier_app)

    def key(x: str) -> str:
        return _norm(x, args.fuzzy)

    set_b = {key(x) for x in b}
    set_a = {key(x) for x in a}

    doar_pdf = [x for x in a if key(x) not in set_b]
    doar_app = [x for x in b if key(x) not in set_a]

    print("=== Doar în fișierul PDF (referință) — posibil lipsă din app ===")
    for x in doar_pdf:
        print(" ", x)
    if not doar_pdf:
        print(" (nimic)")

    print("\n=== Doar în fișierul APP — posibil denumire diferită / în plus ===")
    for x in doar_app:
        print(" ", x)
    if not doar_app:
        print(" (nimic)")

    print(f"\n--- Rezumat: PDF {len(a)} linii | APP {len(b)} linii | doar-PDF {len(doar_pdf)} | doar-APP {len(doar_app)} ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
