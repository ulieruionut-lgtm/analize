# -*- coding: utf-8 -*-
"""Test: parserul extrage toate 24 analize din text Bioclinica sintetic."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Text Bioclinica complet - toate analizele asteptate pentru Nitu Matei
TEXT_24 = """
NITU MATEI M, 1 an
CNP: 5240222080031

Hemoleucogramă
Hematii 4.650.000 /mm³ (3.700.000 - 5.150.000)
Hemoglobină 13,3 g/dL (10,2 - 13,4)
Hematocrit 38,1 % (31,5 - 40,5)
MCV 81,9 fL (72,0 - 93,0)
MCH 28,6 pg (23,5 - 31,0)
MCHC 34,9 g/dL (30,0 - 35,0)
RDW 13,1 % (13,6 - 15,5)
Trombocite 323.000 /mm³ (220.000 - 490.000)
Leucocite 3.980 /mm³ (6.000 - 15.000)

Formula leucocitară
Neutrofile
2.260 /mm³
56,78 %
(1.500 - 8.700)/mm³
(22,00 - 63,00)%
Limfocite
1.150 /mm³
28,89 %
(3.000 - 10.000)/mm³
(18,00 - 56,00)%
Monocite
460 /mm³
11,56 %
(200 - 1.100)/mm³
(4,00 - 12,00)%
Eozinofile
60 /mm³
1,51 %
(0 - 500)/mm³
(0,00 - 6,00)%
Bazofile
50 /mm³
1,26 %
(0 - 200)/mm³
(0,00 - 2,00)%

BIOCHIMIE
Proteina C reactivă
2,260 mg/dL (≤ 0,33)
TGO (ASAT)
74 U/L (9 - 80)
TGP (ALAT)
64 U/L (10 - 40)
Creatinină serică
0,27 mg/dL (0,10 - 0,35)
"""

def main():
    try:
        from backend.parser import extract_rezultate, parse_full_text
    except ImportError:
        print("SKIP: backend nu e instalat (pip install -e .)")
        return

    rez = extract_rezultate(TEXT_24)
    n = len(rez)
    print(f"Analize extrase: {n}")
    for r in rez:
        v = r.valoare if r.valoare is not None else (r.valoare_text or "")
        print(f"  {r.denumire_raw[:50]:50} = {v} {r.unitate or ''}")

    asteptate = 23  # hemograma 9 + formula 10 + biochimie 4
    if n >= asteptate:
        print(f"\nOK: {n} >= {asteptate} analize")
    else:
        print(f"\nEROARE: doar {n} analize, asteptate minim {asteptate}")
        sys.exit(1)

if __name__ == "__main__":
    main()
