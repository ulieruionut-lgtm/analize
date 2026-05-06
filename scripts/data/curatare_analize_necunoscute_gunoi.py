# -*- coding: utf-8 -*-
"""
Redirecționare: ``curatare_gunoi_pipeline.py`` (folosește venv dacă există).
"""
from pathlib import Path
import subprocess
import sys

def _python_exe() -> str:
    root = Path(__file__).resolve().parent
    if sys.platform == "win32":
        for v in (root / "venv" / "Scripts" / "python.exe", root / ".venv" / "Scripts" / "python.exe"):
            if v.is_file():
                return str(v)
    else:
        for v in (root / "venv" / "bin" / "python3", root / "venv" / "bin" / "python",
                  root / ".venv" / "bin" / "python3", root / ".venv" / "bin" / "python"):
            if v.is_file():
                return str(v)
    return sys.executable

if __name__ == "__main__":
    other = Path(__file__).resolve().parent / "curatare_gunoi_pipeline.py"
    raise SystemExit(subprocess.call([_python_exe(), str(other)] + sys.argv[1:]))
