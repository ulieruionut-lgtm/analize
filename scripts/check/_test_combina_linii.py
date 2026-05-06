# -*- coding: utf-8 -*-
"""Test manual al logicii parser pe textul extras din PDF Nitu (fara pydantic)."""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Simulam _combina_linii_bioclinica si RE_VALOARE_LINIE minimal
_RE_VAL_UM_SIMPLU = re.compile(
    r"^([\d.,]+)\s+([a-zA-Z%µμg·²³\u00b3/][a-zA-Z0-9%µμg·²³\u00b3/²³]*)\s*$",
    re.IGNORECASE,
)
_RE_INTERVAL_PARANTEZE = re.compile(
    r"^\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)\s*$"
)

RE_VALOARE_LINIE = re.compile(
    r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\s/]+?)\s*\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)

# Textul exact din PDF Nitu (din debug)
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
    'Interpretare:',
    'Răspuns rapid ........ < 0,4 (ziua 4 de terapie)',
    'Răspuns lent ......... Scădere continuă și lentă a CRP-ratio',
    'Răspuns bifazic ...... Scădere inițială < 0,8 urmată de creștere ≥ 0,8',
    'Răspuns absent ....... ≥ 0,8',
    'Conform studiilor de specialitate, scăderea rapidă a CRP-ratio reprezintă un indicator al răspunsului',
    'favorabil la terapia cu antibiotice, menținerea/creșterea CRP-ratio sugerează o infecție refractară la',
    'tratament.',
    '(ser, turbidimetrie)',
    'TGO (ASAT)',
    'Pagina 1 / 2',
    'NITU MATEI    M, 1 an',
    'CNP', '5240222080031', 'DATA NAȘTERII', '22.02.2024',
    'ADRESA', 'STR Izvorului 28h, Tărlungeni, Brașov',
    'TRIMIS DE', 'medic Coşerea Andreea (H04896)', '00001 Laborator Brașov',
    'Buletin de analize 26213B0679 din 13.02.2026',
    'RECOLTAT', '13.02.2026 11:12', 'LUCRAT', 'Bioclinica SA',
    'STR Ștefan Luchian Pictor 5, Brașov', 'GENERAT', '13.02.2026 15:05',
    'VALORI BIOLOGICE DE REFERINȚĂ', 'ANTECEDENT',
    'Rezultatele se referă numai la proba analizată. Reproducerea totală sau parțială a buletinului de analize se face numai cu acordul BIOCLINICA.',
    'bioclinica.ro', 'F01 - PG22', 'Ed.1, rev.0', '',
    '74 U/L', '(9 - 80)', '(ser, spectrofotometrie)',
    'TGP (ALAT)', '64 U/L', '(10 - 40)', '(ser, spectrofotometrie)',
    'Creatinină serică', '0,27 mg/dL', '(0,10 - 0,35)',
    '24 µmol/L', '(9 - 31)', '(ser, spectrofotometrie)',
]

def combina_linii(lines):
    result = []
    i = 0
    while i < len(lines):
        if i + 1 < len(lines):
            m_val = _RE_VAL_UM_SIMPLU.match(lines[i])
            m_int = _RE_INTERVAL_PARANTEZE.match(lines[i + 1])
            if m_val and m_int:
                combinat = f"{lines[i]} ({m_int.group(1)} - {m_int.group(2)})"
                result.append(combinat)
                i += 2
                continue
        result.append(lines[i])
        i += 1
    return result

lines = combina_linii(lines_raw)
print("=== Linii dupa combinare ===")
for i, l in enumerate(lines):
    if l:
        print(f"  {i:3d}: {l}")

print("\n=== Test RE_VALOARE_LINIE ===")
test_vals = ['74 U/L (9 - 80)', '13,3 g/dL (10,2 - 13,4)', '4.650.000 /mm³ (3.700.000 - 5.150.000)']
for v in test_vals:
    m = RE_VALOARE_LINIE.match(v)
    print(f"  {v!r} -> {'MATCH' if m else 'NO MATCH'} {f'val={m.group(1)}, um={m.group(2).strip()}' if m else ''}")
