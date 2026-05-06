"""
Test local al fix-urilor OCR pe liniile din Trefan Victor
(simuleaza ce va face Railway dupa deploy)
"""
import sys, os
sys.path.insert(0, r"d:\Ionut analize")
os.environ["PYTHONIOENCODING"] = "utf-8"

from backend.ocr_corrections import corecteaza_ocr_linie_buletin
from backend.parser import _parse_oneline, extract_rezultate

linii_trefan = [
    "'Hemoglobina(HGB) = «= £168gd © 12,6-17,4",
    "Hematocrit (HCT) # 470% © 8 0",
    "„Volum mediu eritrocitar (MCV) 857f © fl",
    "Hemoglobina eritrocitara 306pg © 27-35 pg",
    "Con. = 357g 31-36 g/dl",
    '"Indice de distributie eritrocitelor(RDW) 131% © en',
    "Indice de distr. a trombocitelor (PDW) $$162%",
    "4dUreeserica | 465mgdi §§|. © 10-50",
    "serica O | 0,74 mgdi |9 0,8-1,3 mg/dl",
    "Colesterol seric total | 488 mgdi |q Valori normale: 120-200 mg/dl",
    "Rata filtrarii glomerulare 96 mimin Categoriile de GFR conform ml/min",
    "16. Raport albumina creatinina = 1,70 <30 mg/g : albuninurie normalamg/g _",
]

print("=== TEST LOCAL FIX-URI OCR ===\n")
for linie in linii_trefan:
    dupa = corecteaza_ocr_linie_buletin(linie)
    rez = _parse_oneline(dupa)
    print(f"INAINTE: {repr(linie[:80])}")
    print(f"  DUPA:  {repr(dupa[:80])}")
    if rez:
        print(f"  PARSE: {rez.denumire_raw!r:45s} = {rez.valoare!r:10} {rez.unitate!r:15} [{rez.interval_min}-{rez.interval_max}]")
    else:
        print(f"  PARSE: (nicio analiza extrasa)")
    print()
