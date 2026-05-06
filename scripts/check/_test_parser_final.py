# -*- coding: utf-8 -*-
"""Test complet parser simulare cu noua logica - text complet PDF."""
import sys, io, re, fitz
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Definim RE si functii ca in parser.py (subset relevant)
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
RE_VALOARE_PARTIAL = re.compile(r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\s/m]+?)$", re.IGNORECASE)

_LINII_EXCLUSE = re.compile(
    r"^(Buletin|CNP|ADRESA|TRIMIS|LUCRAT|RECOLTAT|GENERAT|Pagina|Rezultatele|"
    r"http|F01|F-0|Ed\.|rev\.|bioclinica|VALORI|medic\s+primar|"
    r"Buletin de analize|"
    r"ANTECEDENT|DATA\s+NA|^TRIMIS\s+DE$|"
    r"^RECOLTAT$|^LUCRAT$|^GENERAT$|^CNP$|"
    r"^STR\s+|^Str\.\s+|"
    r"^medic\s+[A-Za-z]|"
    r"^\d{5}\s+Laborator|"
    r"^[MF]\s*,\s*\d+|"
    r".*\s[MF]\s*,\s*\d+\s*an|"
    r"Aceste\s+rezultate|"
    r"ser,\s+spectrofotometrie|ser,\s+turbidimetrie|sânge\s+integral|"
    r"Hemoleucogramă|Formula\s+leucocitară|"
    r"Interpretare:|Evaluarea\s+răspunsului|CRP-ratio|"
    r"Răspuns\s+rapid|Răspuns\s+lent|Răspuns\s+bifazic|Răspuns\s+absent|"
    r"Conform\s+studiilor|favorabil\s+la\s+terapia|tratament\.)",
    re.IGNORECASE,
)

def _este_linie_parametru(linie):
    if not linie or len(linie) > 150:
        return False
    if _LINII_EXCLUSE.match(linie):
        return False
    if re.search(r"\d{9,}", linie):
        return False
    if re.match(r"^\d{2}\.\d{2}\.\d{4}", linie):
        return False
    if re.match(r'^["\'\[\]\{\}:;|\\(]', linie):
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

path = r'c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\a204ebdd-e453-416b-b7ce-a660fb82f24b\buletin analize 13.02.2026.pdf'
doc = fitz.open(path)
all_text = ""
for page in doc:
    t = page.get_text()
    if t.strip():
        all_text += t + "\n"
doc.close()

lines_raw = [l.strip() for l in all_text.replace("\r", "\n").split("\n")]
lines = combina_linii(lines_raw)

print("=== Pasul 1: format 2 linii Bioclinica (cu fereastra extinsa) ===")
rezultate = []
for i in range(1, len(lines)):
    linie_val = lines[i]
    if not linie_val:
        continue
    m = RE_VALOARE_LINIE.match(linie_val)
    if not m:
        continue
    denumire = ""
    for j in range(i - 1, max(i - 30, -1), -1):
        cand = lines[j].strip()
        if not cand:
            continue
        if _LINII_EXCLUSE.match(cand):
            continue
        if RE_BIOCLINICA_ONELINE.search(cand) or RE_BIOCLINICA_REF_SINGULAR.search(cand):
            break
        if _este_linie_parametru(cand) and not RE_VALOARE_LINIE.match(cand) and not RE_VALOARE_PARTIAL.match(cand):
            denumire = cand
            break
        # Continua daca e non-param non-exclus
    if denumire:
        val = m.group(1)
        um = m.group(2).strip()
        print(f"  {denumire} = {val} {um}")
        rezultate.append(denumire)

print(f"\nTotal: {len(rezultate)} analize")
asteptate = ['Hematii', 'Hemoglobina', 'Hematocrit', 'MCV', 'MCH', 'MCHC', 'RDW',
             'Trombocite', 'Leucocite', 'Neutrofile', 'Limfocite', 'Monocite',
             'Eozinofile', 'Bazofile', 'TGO', 'TGP', 'Creatinina']
print("\nAnalize LIPSA:")
for a in asteptate:
    if not any(a.lower() in r.lower() for r in rezultate):
        print(f"  {a}")
