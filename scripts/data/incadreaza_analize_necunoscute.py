# -*- coding: utf-8 -*-
"""
Încadrează analizele necunoscute la codurile standard corespunzătoare.
Rulează: venv\\Scripts\\python.exe incadreaza_analize_necunoscute.py
         venv\\Scripts\\python.exe incadreaza_analize_necunoscute.py --dry-run
"""
import re
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from backend.database import get_analize_necunoscute, get_cursor, _use_sqlite, _row_get
from backend.parser import este_denumire_gunoi
from backend.normalizer import adauga_alias_nou


def _cod_pentru_denumire(raw: str) -> str | None:
    """Returnează cod_standard pentru denumire_raw sau None dacă e gunoi/fără mapare."""
    if not raw or len(raw.strip()) < 2:
        return None
    s = raw.strip().lower()

    # ─── Analize cunoscute (verificăm ÎNAINTE de gunoi - ex: COLESTEROL TOTAL = 2 cuvinte caps) ───
    if "concentratia medie" in s and "hemoglobin" in s:
        return "MCHC"
    if "largimea distributiei" in s or "coeficient variat" in s:
        return "RDW"
    if "hemoglobina eritrocitara medie" in s or "mch)" in s:
        return "MCH"
    if "numar de eritrocite" in s or "(rbc)" in s and "eritrocite" in s:
        return "RBC"
    if "numar de leucocite" in s or "(wbc)" in s and "leucocite" in s:
        return "WBC"
    if "numar de monocite" in s or "(mon)" in s:
        return "MONOCITE_NR"
    if "numar de bazofile" in s or "(bas)" in s:
        return "BAZOFILE_NR"
    if "distributia plachetelor" in s or "pdw" in s or "(pdw" in s:
        return "PDW"
    if "volumul mediu" in s and ("plachetar" in s or "pla.chetar" in s):
        return "MPV"
    if "colesterol total" in s:
        return "COLESTEROL_TOTAL"

    # ─── Hormoni / biochimie / hematologie (mapare clinică frecventă) ───
    if re.search(r"\bft4\b", s) or (
        "tiroxin" in s and ("liber" in s or "libera" in s or "liberă" in s or "seric" in s or "serica" in s or "serică" in s)
    ):
        return "FT4"
    if re.search(r"\begfr\b|\brfg\b", s) or "filtrare glomerular" in s or "filtrarea glomerular" in s:
        return "EGFR"
    if re.search(r"^\s*(tgp|alt)\b", s) or re.search(r"\b(tgp|alt)\s*\(", s) or re.search(r"\balat\b", s):
        return "ALT"
    if re.search(r"^\s*(tgo|ast)\b", s) or re.search(r"\b(tgo|ast)\s*\(", s) or re.search(r"\basat\b", s):
        return "AST"
    if "feritin" in s:
        return "FERITINA"
    if re.search(r"^\s*vsh\b", s) or ("viteza" in s and "sediment" in s and "hemat" in s):
        return "VSH"
    # Glucoză / glicemie serică (nu linie tip sumar urină „Glucoză Negativ mg/dL”)
    if ("glucoz" in s or "glicem" in s) and "urin" not in s:
        if not ("negativ" in s and ("mg/dl" in s or "mg/dl" in raw.lower())):
            return "GLUCOZA_FASTING"
    if "bilirubin" in s:
        if "direct" in s:
            return "BILIRUBIN_DIR"
        if "indirect" in s:
            return "BILIRUBIN_IND"
        if "total" in s:
            return "BILIRUBIN_TOT"
        # Sumar urină: „Bilirubina Negativ” fără „totală” serică
        if "negativ" in s or "absent" in s:
            return "URINA_SUMAR"
        return "BILIRUBIN_TOT"

    # ─── Microbiologie (înainte de gunoi / urină generic) ───
    if "cultura fungi" in s or "cultura fong" in s or ("cultura" in s and "fungi" in s):
        return "MICRO_CULT_FUNGI"
    if "examen microbiologic" in s:
        return "MICRO_EXAM_MIC"
    if "culturi bacteriene" in s:
        if "absent" in s and len(s) < 50:
            return "__STERGE__"
        return "MICRO_CULT_BACT"
    if ("examen microscopic" in s or "microscopic" in s) and "colorat" in s:
        return "MICRO_MICR_COL"
    if "citobacteriologic" in s:
        return "MICRO_CITO_VAG"
    if "chlamydia" in s:
        return "MICRO_AG_CHLAM"
    if "mycoplasma" in s or "ureaplasma" in s:
        return "MICRO_MYCO_UREA"
    if re.match(r"^candida\s", s):
        return "MICRO_CANDIDA_SPP"
    if "mucus" in s:
        return "URINA_SUMAR"

    # ─── Gunoi - excludem (după verificări analize cunoscute) ───
    if este_denumire_gunoi(raw):
        return "__STERGE__"

    # ─── URINĂ / SEDIMENT ───
    if any(x in s for x in ["leucocit", "leucoclte"]) and ("foarte" in s or "rare" in s or ":" in s):
        return "URINA_SUMAR"
    if any(x in s for x in ["epitelial", "epltehale", "tranzmonale", "tranzitor", "tranzutlonale"]):
        return "URINA_SUMAR"
    if "cristale" in s or "acid uric" in s:
        return "URINA_SUMAR"
    if "eritrocitare)" in s and "hemoglobina" not in s:
        return "URINA_SUMAR"
    if any(x in s for x in ["nitrit", "nitriti", "nitriți"]):
        return "URINA_SUMAR"
    if any(x in s for x in ["urobilinogen", "corpi ceton", "pigmen", "proteine negativ"]):
        return "URINA_SUMAR"
    if "glucoz" in s and ("negativ" in s or "pozitiv" in s or "urin" in s):
        return "URINA_SUMAR"
    if "proteine" in s and ("negativ" in s or not re.search(r"\d", s)):
        return "URINA_SUMAR"
    if "galben" in s or "limpede" in s:
        return "URINA_SUMAR"
    if "12:11 alte" in s or "12,2:2" in s or "1,2:2" in s:
        return "URINA_SUMAR"
    if "foarte rare" in s:
        return "URINA_SUMAR"
    if "albumina urinar" in s or "albumină urinar" in s:
        return "MICROALBUMIN"
    if "creatinina urinar" in s or "creatinină urinar" in s:
        return "CREAT_URINA"
    if "flora bacteriana" in s:
        return "FLORA_URINA"

    # ─── MICROBIOLOGIE (exclude "X spp -" = absent) ───
    if "enterococcus" in s or "streptococcus" in s:
        if " -" in s or s.endswith("-"):
            return "__STERGE__"
        return "FLORA_URINA"

    # ─── Rezultate pure / gunoi OCR ───
    if "negatlv" in s and ("mg/dl" in s or "air" in s or "aar" in s):
        return "__STERGE__"
    if len(s) <= 3 and (not s.replace("î", "i").replace("ă", "a").isalpha() or s in ("îîî", "iii", "îî")):
        return "__STERGE__"
    if any(x in s for x in ["prilie", "arere:", "icod cerere", "c'ed cerere", "c'éd cerere", "u doza"]):
        return "__STERGE__"
    if "border" in s and "crescut" in s and "150" in s:  # Border]me crescut 150
        return "__STERGE__"
    if "bacteriurie" in s and len(s) < 25:  # "Bacteriurie <" incomplet
        return "__STERGE__"

    return None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Afișează ce s-ar face, fără modificare")
    args = parser.parse_args()

    nec = get_analize_necunoscute(doar_neaprobate=True)

    print(f"Analize neaprobate de procesat: {len(nec)}\n")

    from backend.database import _get_or_create_analiza_standard
    _STANDARDE_EXTRA = [
        ("URINA_SUMAR", "Sumar urina"),
        ("FLORA_URINA", "Flora microbiana urina"),
        ("CREAT_URINA", "Creatinina urinară"),
        ("MICRO_CULT_FUNGI", "Cultura fungi"),
        ("MICRO_EXAM_MIC", "Examen microbiologic"),
        ("MICRO_CULT_BACT", "Culturi bacteriene"),
        ("MICRO_MICR_COL", "Examen microscopic colorat"),
        ("MICRO_CITO_VAG", "Examen citobacteriologic secretie vaginala"),
        ("MICRO_AG_CHLAM", "Ag Chlamydia trachomatis"),
        ("MICRO_MYCO_UREA", "Mycoplasma / Ureaplasma"),
        ("MICRO_CANDIDA_SPP", "Candida spp"),
    ]
    for cod, den in _STANDARDE_EXTRA:
        _get_or_create_analiza_standard(cod, den)

    sterse, mapate, nerecunoscute = 0, 0, 0
    for r in nec:
        raw = (r.get("denumire_raw") if isinstance(r, dict) else (r[1] if len(r) > 1 else "")) or ""
        rid = (r.get("id") if isinstance(r, dict) else (r[0] if len(r) > 0 else 0)) or 0
        if not raw:
            continue

        cod = _cod_pentru_denumire(raw)
        if cod == "__STERGE__":
            print(f"  STERGE: {raw[:60]}")
            if not args.dry_run:
                from backend.database import sterge_analiza_necunoscuta
                sterge_analiza_necunoscuta(rid)
            sterse += 1
            continue

        if not cod:
            print(f"  ? Fără mapare: {raw[:60]}")
            nerecunoscute += 1
            continue

        with get_cursor(commit=False) as c:
            ph = "?" if _use_sqlite() else "%s"
            c.execute(f"SELECT id FROM analiza_standard WHERE cod_standard = {ph}", (cod,))
            row = c.fetchone()
        aid = (_row_get(row, "id") or _row_get(row, 0)) if row else None
        if not aid:
            print(f"  SKIP cod {cod} nu există: {raw[:50]}")
            continue

        print(f"  + {raw[:45]} -> {cod}")
        if not args.dry_run:
            adauga_alias_nou(raw.strip(), aid)
        mapate += 1

    from backend.normalizer import invalideaza_cache
    if not args.dry_run:
        invalideaza_cache()

    print(f"\n✓ Mapate: {mapate} | Șterse: {sterse} | Fără mapare: {nerecunoscute}")
    if args.dry_run:
        print("\n[DRY-RUN] Rulează fără --dry-run pentru a aplica.")


if __name__ == "__main__":
    main()
