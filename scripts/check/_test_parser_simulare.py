# -*- coding: utf-8 -*-
"""Test simulare logica parser pe textul PDF Nitu - manual, fara pydantic."""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ---- Copiem definitiile relevante din parser.py ----

_RE_VAL_UM_SIMPLU = re.compile(
    r"^([\d.,]+)\s+([a-zA-Z%µμg·²³\u00b3/][a-zA-Z0-9%µμg·²³\u00b3/²³]*)\s*$",
    re.IGNORECASE,
)
_RE_INTERVAL_PARANTEZE = re.compile(r"^\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)\s*$")

RE_VALOARE_LINIE = re.compile(
    r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\s/]+?)\s*\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)

RE_BIOCLINICA_ONELINE = re.compile(
    r"\s+([\d.,]+)\s+([a-zA-Z/%µμg·²³\u00b3\s/]+?)\s*\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)

RE_BIOCLINICA_REF_SINGULAR = re.compile(
    r"\s+([\d.,]+)\s+([a-zA-Z/%µμg·²³\u00b3\s/]+?)\s*\(\s*[≤≥<>]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)

_LINII_EXCLUSE = re.compile(
    r"^(Buletin|CNP|ADRESA|TRIMIS|LUCRAT|RECOLTAT|GENERAT|Pagina|Rezultatele|"
    r"Reproducerea|Pentru|Nu se|Este|Valori|Opiniile|Analizele|Se utilizeaz|"
    r"http|F01|F-0|Ed\.|rev\.|bioclinica|VALORI|medic\s+primar|"
    r"brasov@|RENAR|seria|serie|Nr\.\s+\d|Buletin de analize|Data tipar|"
    r"Hemoleucogramă|Formula\s+leucocitară|"
    r"ANTECEDENT|DATA\s+NA[SȘŞsşș]TERII|^ADRES[AĂ]$|^TRIMIS\s+DE$|"
    r"^RECOLTAT$|^LUCRAT$|^GENERAT$|^CNP$|"
    r"^STR\s+|^Str\.\s+|"
    r"^medic\s+[A-ZĂÂÎȘȚa-zăâîșț]|"
    r"^\d{5}\s+Laborator|"
    r"^[MF]\s*,\s*\d+\s*(?:ani?|luni?)|"
    r".*\s[MF]\s*,\s*\d+\s*(?:ani?|luni?)|"
    r"Aceste\s+rezultate|"
    r"(ser,\s+spectrofotometrie|ser,\s+turbidimetrie|sânge\s+integral))",
    re.IGNORECASE,
)

def _este_linie_parametru(linie: str) -> bool:
    if not linie or len(linie) > 150:
        return False
    if _LINII_EXCLUSE.match(linie):
        return False
    if re.search(r"\d{9,}", linie):
        return False
    if re.match(r"^\d{2}\.\d{2}\.\d{4}", linie):
        return False
    if re.match(r'^["\'\[\]\{\}:;|\\]', linie):
        return False
    if len(re.sub(r'[^a-zA-Z]', '', linie)) < 3:
        return False
    return True

def combina_linii(lines):
    result = []
    i = 0
    while i < len(lines):
        if i + 1 < len(lines):
            m_val = _RE_VAL_UM_SIMPLU.match(lines[i])
            m_int = _RE_INTERVAL_PARANTEZE.match(lines[i + 1])
            if m_val and m_int:
                result.append(f"{lines[i]} ({m_int.group(1)} - {m_int.group(2)})")
                i += 2
                continue
        result.append(lines[i])
        i += 1
    return result

# Textul extras de fitz din PDF Nitu
lines_raw = [
    'Hemoleucogramă', 'Hematii', '4.650.000 /mm³', '(3.700.000 - 5.150.000)',
    'Hemoglobină', '13,3 g/dL', '(10,2 - 13,4)',
    'Hematocrit', '38,1 %', '(31,5 - 40,5)',
    'MCV', '81,9 fL', '(72,0 - 93,0)',
    'MCH', '28,6 pg', '(23,5 - 31,0)',
    'MCHC', '34,9 g/dL', '(30,0 - 35,0)',
    'RDW', '13,1 %', '(13,6 - 15,5)',
    'Trombocite', '323.000 /mm³', '(220.000 - 490.000)',
    'Leucocite', '3.980 /mm³', '(6.000 - 15.000)',
    'Formula leucocitară', 'Neutrofile', '2.260 /mm³', '56,78 %',
    '(1.500 - 8.700)/mm³', '(22,00 - 63,00)%',
    'Limfocite', '1.150 /mm³', '28,89 %', '(3.000 - 10.000)/mm³', '(32,00 - 63,00)%',
    'Monocite', '460 /mm³', '11,56 %', '(150 - 1.200)/mm³', '(1,50 - 10,50)%',
    'Eozinofile', '60 /mm³', '1,51 %', '(20 - 750)/mm³', '(0,50 - 5,00)%',
    'Bazofile', '50 /mm³', '1,26 %', '(0 - 200)/mm³', '(0,00 - 1,50)%',
    '(sânge integral EDTA, citometrie de flux & citochimie & spectrofotometrie)',
    'Proteina C reactivă', '2,260 mg/dL', '(≤ 0,33)', '22,60 mg/L', '(≤ 3,30)',
    'Evaluarea răspunsului la terapia cu antibiotice:',
    'CRP-ratio (raport) - concentrație zilnică CRP/concentrație CRP ziua 0',
    'Interpretare:', 'Răspuns rapid ........ < 0,4 (ziua 4 de terapie)',
    'tratament.', '(ser, turbidimetrie)',
    'TGO (ASAT)', 'Pagina 1 / 2', 'NITU MATEI    M, 1 an',
    'CNP', '5240222080031', 'DATA NAȘTERII', '22.02.2024',
    'ADRESA', 'STR Izvorului 28h, Tărlungeni, Brașov',
    'TRIMIS DE', 'medic Coşerea Andreea (H04896)', '00001 Laborator Brașov',
    'Buletin de analize 26213B0679 din 13.02.2026',
    'RECOLTAT', '13.02.2026 11:12', 'LUCRAT', 'Bioclinica SA',
    'STR Ștefan Luchian Pictor 5, Brașov', 'GENERAT', '13.02.2026 15:05',
    'VALORI BIOLOGICE DE REFERINȚĂ', 'ANTECEDENT',
    'Rezultatele se referă numai la proba analizată.',
    'bioclinica.ro', 'F01 - PG22', 'Ed.1, rev.0', '',
    '74 U/L', '(9 - 80)', '(ser, spectrofotometrie)',
    'TGP (ALAT)', '64 U/L', '(10 - 40)', '(ser, spectrofotometrie)',
    'Creatinină serică', '0,27 mg/dL', '(0,10 - 0,35)',
    '24 µmol/L', '(9 - 31)', '(ser, spectrofotometrie)',
]

lines = combina_linii(lines_raw)

print("=== Test excluderi linii header ===")
for l in ['NITU MATEI    M, 1 an', 'DATA NAȘTERII', 'ANTECEDENT', 'ADRESA', 'TRIMIS DE', 
          'RECOLTAT', 'LUCRAT', 'GENERAT', 'STR Izvorului 28h', 'medic Coşerea Andreea (H04896)',
          'TGO (ASAT)', 'Hematii', 'Hemoglobină']:
    excl = bool(_LINII_EXCLUSE.match(l))
    param = _este_linie_parametru(l)
    print(f"  {'EXCLUS' if excl else 'OK'} / {'param' if param else 'non-param'}: {l!r}")

print("\n=== Simulare Pasul 1 (format doua linii Bioclinica) ===")
rezultate_gasite = []
for i in range(1, len(lines)):
    linie_val = lines[i]
    if not linie_val:
        continue
    m = RE_VALOARE_LINIE.match(linie_val)
    if not m:
        continue
    valoare = linie_val
    denumire = ""
    for j in range(i - 1, max(i - 30, -1), -1):
        cand = lines[j].strip()
        if not cand:
            continue
        if _LINII_EXCLUSE.match(cand):
            continue
        if RE_BIOCLINICA_ONELINE.search(cand) or RE_BIOCLINICA_REF_SINGULAR.search(cand):
            break
        if _este_linie_parametru(cand) and not RE_VALOARE_LINIE.match(cand):
            denumire = cand
        break
    if denumire:
        print(f"  {denumire!r} = {m.group(1)} {m.group(2).strip()}")
        rezultate_gasite.append(denumire)

print(f"\nTotal analize gasite: {len(rezultate_gasite)}")
print("\nAnalize LIPSA din PDF:")
asteptate = ['Hematii', 'Hemoglobină', 'Hematocrit', 'MCV', 'MCH', 'MCHC', 'RDW', 
             'Trombocite', 'Leucocite', 'Neutrofile', 'Limfocite', 'Monocite', 
             'Eozinofile', 'Bazofile', 'Proteina C reactivă', 'TGO (ASAT)', 
             'TGP (ALAT)', 'Creatinină serică']
for a in asteptate:
    gasit = any(a.lower() in r.lower() for r in rezultate_gasite)
    if not gasit:
        print(f"  LIPSA: {a}")
