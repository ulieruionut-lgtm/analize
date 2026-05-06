# -*- coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

T = chr(9)
REF = f"""3. Biochimie serică
Test{T}Rezultat{T}Unitate{T}Interval de referință
Trigliceride serice{T}66{T}mg/dL{T}Optim <150
Creatinină (serică){T}0,9{T}mg/dL{T}0,7 – 1,36
eGFR (CKD-EPI 2021){T}86,88{T}ml/min/1,73 m²{T}G2 note
6. Hemoleucogramă (CBC)
Test{T}Rezultat{T}Unitate{T}Interval
WBC (leucocite){T}5,15{T}10³/μL{T}4 – 10
PLT (trombocite){T}142{T}10³/μL{T}150 – 400
MPV (volum){T}10,5{T}fL{T}7,4 – 13
7. Markeri tumorali
Test{T}Rezultat{T}Unitate{T}Interval
PSA total{T}0,482{T}ng/mL{T}0 – 4,4
2. Antibiogramă (test)
Antibiotic{T}Interpretare
Amikacina{T}Sensibil
Ampicilina{T}Rezistent
"""


def main() -> None:
    from backend.parser import extract_rezultate

    rows = extract_rezultate(REF)
    print("count", len(rows))
    for i, r in enumerate(rows, 1):
        c = (getattr(r, "categorie", None) or "")[:14]
        print(f"{i:3}. [{c:<14}] {r.denumire_raw!r} v={r.valoare!r} vt={(r.valoare_text or '')[:30]!r}")


if __name__ == "__main__":
    main()
