"""Testeaza parser-ul pe text Nitu (Bioclinica)."""
import sys
sys.stdout.reconfigure(encoding="utf-8")

# Text extras din PDF Nitu (primele pagini)
TEXT_NITU = """
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
Neutrofile 2.260 /mm³ 56,78 % (1.500 - 8.700)/mm³
Limfocite 1.150 /mm³ 28,89 % (3.000 - 10.000)/mm³
Proteina C reactivă
2,260 mg/dL (≤ 0,33)
TGO (ASAT)
74 U/L (9 - 80)
TGP (ALAT)
64 U/L (10 - 40)
Creatinină serică
0,27 mg/dL (0,10 - 0,35)
"""

# Ruleaza cu: python test_nitu_parser.py (din directorul proiectului, cu backend instalat)
try:
    from backend.parser import extract_rezultate

    rez = extract_rezultate(TEXT_NITU)
    print(f"Extrase {len(rez)} rezultate:\n")
    for r in rez:
        v = r.valoare if r.valoare is not None else r.valoare_text
        print(f"  {r.denumire_raw[:45]:45} -> {v} {r.unitate or ''}")
except Exception as e:
    print("Eroare:", e)
    import traceback
    traceback.print_exc()
