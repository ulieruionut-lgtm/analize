# -*- coding: utf-8 -*-
"""
Adaugă aliasuri pentru analizele necunoscute conform mapării corecte.
Invată aplicația să recunoască automat aceste denumiri la upload-uri viitoare.
Rulează: venv\\Scripts\\python.exe adauga_aliasuri_analize_necunoscute.py
"""
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Asociere corectă conform specificațiilor utilizatorului
# Format: (alias, cod_standard)
URINA = "URINA_SUMAR"  # Sumar urina (examen complet)
CREAT_URINA = "CREAT_URINA"  # Creatinina urinară
CREATININA = "CREATININA"  # Creatinina serică
MICROALBUMIN = "MICROALBUMIN"  # Microalbuminurie / albumină urinară
HCT = "HCT"
HB = "HB"  # Hemoglobină
MCV = "MCV"
MCHC = "MCHC"
MCH = "MCH"
RDW = "RDW"
RBC = "RBC"
WBC = "WBC"
PLT = "PLT"  # Trombocite
PDW = "PDW"
MPV = "MPV"
ALT = "ALT"  # TGP / ALAT
AST = "AST"  # TGO / ASAT
GLICEMIE = "GLUCOZA_FASTING"
FLORA_URINA = "FLORA_URINA"  # Flora microbiana / bacteriologie urocultură

MAPARI = [
    # ---- URINĂ (SUMAR + SEDIMENT) ----
    ("Leucocite : foarte rare", URINA),
    ("Leucocite : foarte", URINA),
    ("Leucocite * : foarte rare", URINA),   # variantă cu asterisk din PDF
    ("Leucocite * : foarte", URINA),
    ("Nitriti Negativ (Negativ)", URINA),
    ("Nitriti Negativ (Negativ) Negativ", URINA),
    ("Nitriti", URINA),
    ("Urobilinogen", URINA),
    ("Urobilinogen Normal (Normal)", URINA),
    ("Proteine Negativ (Negativ)", URINA),
    ("Proteine Negativ mg/dL", URINA),
    ("Proteine Negativ mg/dL. -", URINA),   # variantă cu . - la sfârșit
    ("Glucoză Normal (Normal)", URINA),
    ("Corpi cetonici", URINA),
    ("Corpi cetonici Negativ (Negativ)", URINA),
    ("Pigmenți biliari", URINA),
    ("Pigmenți biliari Negativ (Negativ)", URINA),
    ("Galben", URINA),
    ("Limpede", URINA),
    ("Creatinină urinară", CREAT_URINA),
    ("Creatinina urinară", CREAT_URINA),
    ("Cristale amorfe", URINA),
    ("1.2.10 Cristale amorfe", URINA),       # prefix Regina Maria
    ("Cristale acid uric", URINA),
    ("Celule epiteliale scuamoase", URINA),
    ("Celule epiteliale tranzitorii", URINA),
    ("Il epitheliale tranzitoriale", URINA),  # OCR: Il = Celule
    ("l epltehale tranzmonale", URINA),       # OCR: epiteliale tranzitorii
    ("12:11 Alte", URINA),                    # sediment "Alte" cu prefix
    ("Calciu'urinar.", "CALCIU"),             # OCR: Calciu urinar
    ("eritrocitare)", URINA),
    ("8 epiteliale tranzmonale", URINA),  # OCR pentru tranzitorii
    # ---- HEMATOLOGIE ----
    ("Hematocrit (HCT)", HCT),
    ("Volumul mediu eritrocitar (MCV)", MCV),
    ("Volumul mediu eritrocitar", MCV),
    ("MCHC", MCHC),
    ("MCH", MCH),
    ("Concentrația medie a hemoglobinei eritrocitare (MCHC)", MCHC),
    ("Hemoglobina eritrocitară medie (MCH)", MCH),
    ("Lărgimea distribuției eritrocitare - coeficient variație (RDW-CV)", RDW),
    ("Număr de eritrocite (RBC)", RBC),
    ("Număr de leucocite (WBC)", WBC),
    ("Distribuția plachetelor (PDW-SD)", PDW),
    ("Volumul mediu plachetar (MPV)", MPV),
    ("Volumul mediu plachetar (MPV) (duplicat OCR)", MPV),
    # ---- URINĂ (suplimentar) ----
    ("Nitriți Negativ mg/dL", URINA),
    ("Albumină urinară", MICROALBUMIN),
    ("Albumina urinară", MICROALBUMIN),
    # ---- MICROBIOLOGIE (Flora urocultură) ----
    ("Enterococcus spp", FLORA_URINA),
    ("Enterococcus spp *", FLORA_URINA),
    ("Streptococcus spp", FLORA_URINA),
    ("Streptococcus spp *", FLORA_URINA),
    # ---- HEMOLEUCOGRAMĂ (suplimentar) ----
    ("Hemoglobină", HB),
    ("Hemoglobina", HB),
    ("Hematocrit", HCT),
    ("Trombocite", PLT),
    ("Leucocite", WBC),
    # ---- BIOCHIMIE ----
    ("TGP (ALAT)", ALT),
    ("TGP", ALT),
    ("ALAT", ALT),
    ("TGO (ASAT)", AST),
    ("TGO", AST),
    ("ASAT", AST),
    ("Creatinină serică", CREATININA),
    ("Creatinina serică", CREATININA),
    ("Creatinina", CREATININA),
    ("Glucoză", GLICEMIE),
    ("Glicemie", GLICEMIE),
]


def get_id_by_cod(cod: str) -> int | None:
    from backend.database import get_cursor, _use_sqlite, _row_get
    with get_cursor(commit=False) as cur:
        ph = "?" if _use_sqlite() else "%s"
        cur.execute(f"SELECT id FROM analiza_standard WHERE cod_standard = {ph}", (cod,))
        row = cur.fetchone()
        if row:
            return _row_get(row, 0 if _use_sqlite() else "id")
    return None


def main():
    from backend.database import _get_or_create_analiza_standard
    from backend.normalizer import adauga_alias_nou

    # Asigură că analizele există (creează dacă lipsesc)
    for cod, denumire in [
        ("FLORA_URINA", "Flora microbiana urina"),
        ("CREAT_URINA", "Creatinina urinară"),
        ("URINA_SUMAR", "Sumar urina (examen complet)"),
    ]:
        _get_or_create_analiza_standard(cod, denumire)

    print("=== Adaug aliasuri pentru analize necunoscute ===\n")
    ok, skip = 0, 0

    for alias, cod in MAPARI:
        aid = get_id_by_cod(cod)
        if not aid:
            print(f"  SKIP: cod '{cod}' nu există")
            skip += 1
            continue
        try:
            adauga_alias_nou(alias.strip(), aid)
            print(f"  + '{alias}' -> {cod} (id={aid})")
            ok += 1
        except Exception as e:
            print(f"  ! '{alias}': {e}")
            skip += 1

    print(f"\n✓ Adăugate: {ok} | Sărite: {skip}")
    print("\nAplicația a învățat aceste asocieri. La următorul upload vor fi mapate automat.")
    print("Pentru rezultate pure (Negativ, Normal etc.) rulează curatare_analize_necunoscute_gunoi.py")


if __name__ == "__main__":
    main()
