# -*- coding: utf-8 -*-
"""Simulare completa a parserului pe textul PDF Nitu cu toate fix-urile."""
import sys, io, re, fitz
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ====== Copie exacta a definitiilor din parser.py ======

_RE_VAL_UM_SIMPLU = re.compile(
    r"^([\d.,]+)\s+([a-zA-Z%µμg·²³\u00b3/][a-zA-Z0-9%µμg·²³\u00b3/²³]*)\s*$",
    re.IGNORECASE,
)
_RE_INTERVAL_PARANTEZE = re.compile(
    r"^\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)[^\d\n]*$"
)
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
RE_VALOARE_PARTIAL = re.compile(
    r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\s/m]+?)$",
    re.IGNORECASE,
)
_LINIE_NOTA = re.compile(r"^\(|^\s*\(")

_LINII_EXCLUSE = re.compile(
    r"^(Buletin|CNP|ADRESA|TRIMIS|LUCRAT|RECOLTAT|GENERAT|Pagina|Rezultatele|"
    r"Reproducerea|Pentru|Nu se|Este|Valori|Opiniile|Analizele|Se utilizeaz|"
    r"http|F01|F-0|Ed\.|rev\.|bioclinica|VALORI|medic\s+primar|"
    r"brasov@|RENAR|Buletin de analize|"
    r"Hemoleucogramă|Formula\s+leucocitară|BIOCHIMIE|IMUNOLOGIE|"
    r"ANTECEDENT|DATA\s+NA[SȘŞsşș]TERII|^ADRES[AĂ]$|^TRIMIS\s+DE$|"
    r"^RECOLTAT$|^LUCRAT$|^GENERAT$|^CNP$|"
    r"^STR\s+|^Str\.\s+|"
    r"^medic\s+[A-Za-z]|"
    r"^\d{5}\s+Laborator|"
    r"^[MF]\s*,\s*\d+\s*(?:ani?|luni?)|"
    r".*\s[MF]\s*,\s*\d+\s*(?:ani?|luni?)|"
    r"Aceste\s+rezultate|"
    r"ser,\s+spectrofotometrie|ser,\s+turbidimetrie|sânge\s+integral|"
    r"Conform\s+studiilor|favorabil\s+la|tratament\.|"
    r"Evaluarea\s+răspunsului|CRP-ratio|Interpretare:|"
    r"Răspuns\s+rapid|Răspuns\s+lent|Răspuns\s+bifazic|Răspuns\s+absent)",
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
    if re.match(r'^["\'\[\]\{\}:;|\\]', linie):
        return False
    if len(re.sub(r'[^a-zA-Z]', '', linie)) < 3:
        return False
    return True

def combina_linii(lines):
    result = []
    i = 0
    while i < len(lines):
        if i + 3 < len(lines):
            mv1 = _RE_VAL_UM_SIMPLU.match(lines[i])
            mv2 = _RE_VAL_UM_SIMPLU.match(lines[i + 1])
            mi1 = _RE_INTERVAL_PARANTEZE.match(lines[i + 2])
            mi2 = _RE_INTERVAL_PARANTEZE.match(lines[i + 3])
            if mv1 and mv2 and mi1 and mi2:
                um1 = mv1.group(2).strip()
                um2 = mv2.group(2).strip()
                if um2 == "%" and um1 != "%":
                    result.append(f"{lines[i]} ({mi1.group(1)} - {mi1.group(2)})")
                    param_precedent = ""
                    for prev in reversed(result[:-1]):
                        if prev and not _LINII_EXCLUSE.match(prev):
                            if not RE_VALOARE_LINIE.match(prev) and not _RE_VAL_UM_SIMPLU.match(prev):
                                if len(re.sub(r'[^a-zA-Z]', '', prev)) >= 3:
                                    param_precedent = prev
                                    break
                    if param_precedent:
                        result.append(f"{param_precedent} %")
                    result.append(f"{lines[i + 1]} ({mi2.group(1)} - {mi2.group(2)})")
                    i += 4
                    continue
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

def parse_european(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        if "," in s:
            cleaned = s.replace(".", "").replace(",", ".")
            return float(cleaned)
        cleaned = s.replace(",", ".")
        digits_only = re.sub(r"[^0-9]", "", s)
        if len(digits_only) >= 4 and "." in s:
            cleaned = s.replace(".", "")
            return float(cleaned)
        return float(cleaned)
    except ValueError:
        return None

# ====== Extrage text PDF ======
path = r'c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\1c519765-1585-4cfd-96c0-93bed9dae410\buletin analize 13.02.2026.pdf'
doc = fitz.open(path)
all_text = ""
for page in doc:
    t = page.get_text()
    if t.strip():
        all_text += t + "\n"
doc.close()

lines_raw = [l.strip() for l in all_text.replace("\r", "\n").split("\n")]
lines = combina_linii(lines_raw)

print("=== LINII DUPA COMBINARE ===")
for i, l in enumerate(lines):
    if l:
        print(f"  {i:3d}: {l}")

print("\n=== SIMULARE PARSER (Pasul 1 - doua linii Bioclinica) ===")
rezultate = []
for i in range(1, len(lines)):
    linie_val = lines[i]
    if not linie_val:
        continue
    m = RE_VALOARE_LINIE.match(linie_val)
    if not m:
        # Verifica format singular (≤ X)
        m_sing = re.match(
            r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\s/]+?)\s*\(\s*[≤≥<>]\s*([\d.,]+)\s*\)",
            linie_val, re.IGNORECASE
        )
        if not m_sing:
            continue
        valoare_str = m_sing.group(1)
        unitate = m_sing.group(2).strip()
    else:
        valoare_str = m.group(1)
        unitate = m.group(2).strip()

    valoare = parse_european(valoare_str)
    if valoare is None:
        continue

    denumire = ""
    for j in range(i - 1, max(i - 30, -1), -1):
        cand = lines[j].strip()
        if not cand or _LINIE_NOTA.match(cand):
            continue
        if _LINII_EXCLUSE.match(cand):
            continue
        if RE_BIOCLINICA_ONELINE.search(cand) or RE_BIOCLINICA_REF_SINGULAR.search(cand):
            break
        if RE_VALOARE_LINIE.match(cand):
            break
        if _este_linie_parametru(cand) and not RE_VALOARE_PARTIAL.match(cand):
            denumire = cand
            break

    if denumire:
        rezultate.append((denumire, valoare, unitate))
        print(f"  {denumire} = {valoare} {unitate}")

print(f"\nTotal: {len(rezultate)} analize")

# Compara cu ce ar trebui sa fie
print("\n=== CE CONTINE PDF-ul (toate analizele) ===")
asteptate = {
    'Hematii': ('4.650.000', '/mm³'),
    'Hemoglobină': ('13,3', 'g/dL'),
    'Hematocrit': ('38,1', '%'),
    'MCV': ('81,9', 'fL'),
    'MCH': ('28,6', 'pg'),
    'MCHC': ('34,9', 'g/dL'),
    'RDW': ('13,1', '%'),
    'Trombocite': ('323.000', '/mm³'),
    'Leucocite': ('3.980', '/mm³'),
    'Neutrofile': ('2.260', '/mm³'),
    'Neutrofile %': ('56,78', '%'),
    'Limfocite': ('1.150', '/mm³'),
    'Limfocite %': ('28,89', '%'),
    'Monocite': ('460', '/mm³'),
    'Monocite %': ('11,56', '%'),
    'Eozinofile': ('60', '/mm³'),
    'Eozinofile %': ('1,51', '%'),
    'Bazofile': ('50', '/mm³'),
    'Bazofile %': ('1,26', '%'),
    'Proteina C reactivă (mg/dL)': ('2,260', 'mg/dL'),
    'TGO (ASAT)': ('74', 'U/L'),
    'TGP (ALAT)': ('64', 'U/L'),
    'Creatinină serică': ('0,27', 'mg/dL'),
}
for analiza, (val, um) in asteptate.items():
    gasit = any(analiza.lower() in r[0].lower() for r in rezultate)
    status = "OK" if gasit else "LIPSA"
    print(f"  [{status}] {analiza} = {val} {um}")
