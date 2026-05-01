#!/usr/bin/env python3
"""Verificare locală înainte de deploy: teste parser + afișare parser_version așteptat.

După push pe Railway, compară răspunsul GET /health cu valorile de aici:
  - parser_version trebuie să coincidă exact cu _PARSER_VERSION din backend/main.py
  - build_stamp trebuie să reflecteze BUILD_VERSION scris la build (vezi Dockerfile)
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _parser_version_from_code() -> str:
    text = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    m = re.search(r'^_PARSER_VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else "?"


def _build_stamp_from_dockerfile() -> str | None:
    df = ROOT / "Dockerfile"
    if not df.is_file():
        return None
    t = df.read_text(encoding="utf-8")
    m = re.search(r'echo\s+"([^"]+)"\s*>\s*/app/BUILD_VERSION', t)
    return m.group(1) if m else None


def main() -> int:
    pv = _parser_version_from_code()
    bs = _build_stamp_from_dockerfile()
    print("=== Verificare release parser (local) ===\n", flush=True)
    print(f"parser_version așteptat (cod): {pv}", flush=True)
    if bs:
        print(f"build_stamp așteptat (Dockerfile): {bs}", flush=True)
    print(flush=True)

    tests = [
        "backend/tests/test_parser_text_fixtures.py",
        "backend/tests/test_lab_detect_mentions.py",
    ]
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *tests],
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        print("\n[FAIL] pytest — corectează înainte de deploy.")
        return proc.returncode

    print("\n[OK] Testele parser au trecut.")
    print("\nDupă deploy, verifică producția (înlocuiește host-ul):")
    print(f'  curl -sS "https://analize-production.up.railway.app/health"')
    print("JSON: parser_version și build_stamp trebuie să coincidă cu valorile de mai sus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
