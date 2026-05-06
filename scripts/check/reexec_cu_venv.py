# -*- coding: utf-8 -*-
"""
Dacă există venv/.venv în rădăcina proiectului, re-rulează același script cu
Python-ul din mediu (evită ModuleNotFoundError: pydantic_settings etc.).

Folosit de scripturi CLI din rădăcină: reexec_cu_venv_if_needed(__file__)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _venv_python_candidates(project_root: Path) -> list[Path]:
    if sys.platform == "win32":
        return [
            project_root / "venv" / "Scripts" / "python.exe",
            project_root / ".venv" / "Scripts" / "python.exe",
        ]
    return [
        project_root / "venv" / "bin" / "python3",
        project_root / "venv" / "bin" / "python",
        project_root / ".venv" / "bin" / "python3",
        project_root / ".venv" / "bin" / "python",
    ]


def reexec_cu_venv_if_needed(script_file: str) -> None:
    """
    project_root = folderul unde e scriptul (presupus rădăcina repo-ului).
    """
    root = Path(script_file).resolve().parent
    here = Path(sys.executable).resolve()
    for py in _venv_python_candidates(root):
        try:
            if py.is_file() and py.resolve() != here:
                rc = subprocess.run([str(py), str(Path(script_file).resolve()), *sys.argv[1:]])
                raise SystemExit(rc.returncode)
        except OSError:
            continue


def mesaj_lipsa_dependente(lipseste_modul: str, script_file: str) -> str:
    root = Path(script_file).resolve().parent
    if sys.platform == "win32":
        py = root / "venv" / "Scripts" / "python.exe"
    else:
        py = root / "venv" / "bin" / "python3"
    return (
        f"Lipsește modulul „{lipseste_modul}” — folosești Python fără dependențele proiectului.\n\n"
        f"Opțiuni:\n"
        f"  1) Rulează cu venv:\n"
        f"     {py} {Path(script_file).name} {' '.join(sys.argv[1:])}\n\n"
        f"  2) Instalează dependențele (în același Python):\n"
        f"     pip install -r requirements.txt\n"
    )
