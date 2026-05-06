"""
Debug detaliat pentru liniile care dau None
"""
import sys, os, re
sys.path.insert(0, r"d:\Ionut analize")
os.environ["PYTHONIOENCODING"] = "utf-8"

from backend.ocr_corrections import corecteaza_ocr_linie_buletin
from backend.parser import _parse_oneline, _linie_este_exclusa, _este_denumire_gunoi_heuristic

probleme = [
    'Hematocrit (HCT) # 470% © 8 0',
    '"Indice de distributie eritrocitelor(RDW) 131% © en',
    'Indice de distr. a trombocitelor (PDW) $$162%',
    '4dUreeserica | 465mgdi §§|. © 10-50',
    '16. Raport albumina creatinina = 1,70 <30 mg/g : albuninurie normalamg/g _',
]

for linie in probleme:
    dupa = corecteaza_ocr_linie_buletin(linie)
    print(f"LINIE: {repr(linie[:90])}")
    print(f"DUPA:  {repr(dupa[:90])}")
    
    # Verifica daca linia e exclusa
    if _linie_este_exclusa(dupa):
        print(f"  -> EXCLUSA de _linie_este_exclusa")
    
    # Cauta valoarea
    m_val = re.search(
        r"(?<!\S)(?:[<>≤≥]\s*)?(\d+[.,]\d+|\d+)\s+"
        r"(\*[\w/.^µμ·]+|10\^[\d]+/[a-zA-ZµμL]+|[a-zA-Z%µμg·²³'\/][a-zA-Z0-9%µμg·²³'\/\*\^\.·]*)"
        r"(?:\s+|$)",
        dupa,
    )
    if m_val:
        name = dupa[:m_val.start()].strip()
        print(f"  -> m_val ok: val={m_val.group(1)!r}, unit={m_val.group(2)!r}, name={name!r}")
        if _este_denumire_gunoi_heuristic(name):
            print(f"  -> name e GUNOI: {name!r}")
        if _linie_este_exclusa(name):
            print(f"  -> name EXCLUS: {name!r}")
    else:
        print(f"  -> m_val NOT FOUND")
    
    rez = _parse_oneline(dupa)
    print(f"  -> PARSE: {rez}")
    print()
