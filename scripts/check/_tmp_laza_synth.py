import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.parser import extract_rezultate

text = """
CNP 1234567890123
Nume: LAZA Ion
BIOCHIMIE
COLESTEROL TOTAL                                                  297.89 mg/dL                <200
EXAMEN COMPLET DE URINA
BIOCHIMIE URINA
pH urinar                                                      6                             [5 - 7]
Densitate urinara                                            1020                     [1010 - 1030]
Bilirubina                                                             Negativ                             Negativ
Urobilinogen                                                      Normal                        Normal, <1 mg/dL
Glucoza urinara                                                      Normal                        Normal, <25 mg/dl
Corpi cetonici Absenti Absenti, 2 mg/dl
Eritrocite Absente Absente, <10/uL
Leucocite Negativ Negativ, <10/uL
Nitriti Absenti Absenti
Proteine urinare Absente Absente, <25 mg/dl
Culoare Galben deschis Galben, Galben deschis
Claritate Clar Clar
SEDIMENT URINAR
Celule epiteliale plate Foarte rare Foarte rare, Rare
Leucocite Foarte rare Foarte rare, Rare
Eritrocite Absente Absente, Foarte rare, Rare
Flora bacteriana Absenta Absenta, Foarte rara, Rara
Celule epiteliale rotunde Absente Absente, Foarte rare
Mucus                                                     Prezent                        Absent, Rar
MICROBIOLOGIE
Rezultat cantitativ: Bacteriurie <1000 UFC/mL interpretare absenta cresterii
"""

rs = extract_rezultate(text)
print("COUNT", len(rs))
for r in rs:
    v = r.valoare if r.valoare is not None else (r.valoare_text or "")
    print("-", (r.denumire_raw or "")[:60], "|", v, "|", r.rezultat_tip or "")
