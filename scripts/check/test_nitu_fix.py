# -*- coding: utf-8 -*-
"""Test parser pe textul REAL extras din PDF Nitu (pdfplumber)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Text EXACT din _output_nitu.txt (pdfplumber)
TEXT = """
NITU MATEI
M, 1 an
Buletin de analize 26213B0679 din 13.02.2026
CNP 5240222080031 DATA NASTERII 22.02.2024 RECOLTAT 13.02.2026 11:12
ADRESA STR Izvorului 28h, Tarlungeni, Brasov LUCRAT Bioclinica SA
TRIMIS DE medic Coserea Andreea (H04896) STR Stefan Luchian Pictor 5, Brasov
00001 Laborator Brasov GENERAT 13.02.2026 15:05
VALORI BIOLOGICE DE REFERINTA ANTECEDENT
Hemoleucograma
Hematii 4.650.000/mm3 (3.700.000 - 5.150.000)
Hemoglobina 13,3g/dL (10,2 - 13,4)
Hematocrit 38,1% (31,5 - 40,5)
MCV 81,9fL (72,0 - 93,0)
MCH 28,6pg (23,5 - 31,0)
MCHC 34,9g/dL (30,0 - 35,0)
RDW 13,1% (13,6 - 15,5)
Trombocite 323.000/mm3 (220.000 - 490.000)
Leucocite 3.980/mm3 (6.000 - 15.000)
Formula leucocitara
Neutrofile 2.260/mm3 56,78 % (1.500 - 8.700)/mm3
(22,00 - 63,00)%
Limfocite 1.150/mm3 28,89 % (3.000 - 10.000)/mm3
(32,00 - 63,00)%
Monocite 460/mm3 11,56 % (150 - 1.200)/mm3
(1,50 - 10,50)%
Eozinofile 60/mm3 1,51 % (20 - 750)/mm3
(0,50 - 5,00)%
Bazofile 50/mm3 1,26 % (0 - 200)/mm3
(0,00 - 1,50)%
(sange integral EDTA, citometrie de flux & citochimie & spectrofotometrie)
Proteina C reactiva
2,260mg/dL (<= 0,33)
22,60mg/L (<= 3,30)
Evaluarea raspunsului la terapia cu antibiotice:
TGO (ASAT)
Rezultatele se refera numai la proba analizata.
F01 - PG22 Pagina 1 / 2 Ed.1, rev.0
NITU MATEI
M, 1 an
CNP 5240222080031 DATA NASTERII 22.02.2024 RECOLTAT 13.02.2026 11:12
ADRESA STR Izvorului 28h, Tarlungeni, Brasov LUCRAT Bioclinica SA
00001 Laborator Brasov GENERAT 13.02.2026 15:05
VALORI BIOLOGICE DE REFERINTA ANTECEDENT
74U/L (9 - 80)
(ser, spectrofotometrie)
TGP (ALAT)
64U/L (10 - 40)
(ser, spectrofotometrie)
Creatinina serica
0,27mg/dL (0,10 - 0,35)
24umol/L (9 - 31)
"""

def main():
    try:
        from backend.parser import extract_rezultate, parse_full_text
    except ImportError as e:
        print("Import error:", e)
        return

    rez = extract_rezultate(TEXT)
    n = len(rez)
    print(f"Analize extrase: {n}")
    for r in rez:
        v = r.valoare if r.valoare is not None else (r.valoare_text or "")
        print(f"  {r.denumire_raw[:50]:50} = {v} {r.unitate or ''}")

    asteptate = ["Hematii", "Hemoglobina", "Hematocrit", "MCV", "MCH", "MCHC", "RDW",
                 "Trombocite", "Leucocite", "Neutrofile", "Limfocite", "Monocite",
                 "Eozinofile", "Bazofile", "Proteina C", "TGO", "TGP", "Creatinina"]
    gasite = [r.denumire_raw.lower() for r in rez]
    lipsa = [a for a in asteptate if not any(a.lower() in g for g in gasite)]
    if lipsa:
        print(f"\nLIPSA: {lipsa}")
    else:
        print(f"\nOK: toate cele {len(asteptate)} categorii gasite")
    if n < 20:
        print(f"\nEROARE: doar {n} analize (asteptate 20+)")
        sys.exit(1)

if __name__ == "__main__":
    main()
