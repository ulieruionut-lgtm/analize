"""Test normalizer cu variatii Laza."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway")

from backend.normalizer import _cauta_in_cache

tests = [
    "umar de eozinofile (EOS)",
    "umar de neutrofile (NEUT) :",
    "Largimea distributiei eritrocitare - coeficient variatie (RDW CV)",
    "FIER SERIC (SIDEREMIE) [197.52 wo/a]",
    "HOMOCISTEINA *",
]
for t in tests:
    aid = _cauta_in_cache(t)
    s = f"OK: {t[:50]}... -> {aid}" if len(t) > 50 else f"OK: {t} -> {aid}"
    print(s if aid else f"MISS: {t}")
