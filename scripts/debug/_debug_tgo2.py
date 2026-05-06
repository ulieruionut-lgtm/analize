# -*- coding: utf-8 -*-
"""Debug de ce TGO nu e gasit - versiune standalone."""
import sys, io, re, fitz
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

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

# Pattern simplificat pentru test (subset din _LINII_EXCLUSE real)
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
    r"ser,\s+spectrofotometrie|ser,\s+turbidimetrie|sânge\s+integral)",
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

# Gaseste indexul lui "74 U/L"
tgo_search_i = None
for i, l in enumerate(lines):
    if '74' in l and 'U/L' in l and '9' in l:
        tgo_search_i = i
        print(f"Linia {i}: {repr(l)}")
        break

if tgo_search_i:
    print("\nCautare inapoi pentru TGO:")
    for j in range(tgo_search_i - 1, max(tgo_search_i - 35, -1), -1):
        cand = lines[j]
        excl = bool(_LINII_EXCLUSE.match(cand)) if cand else True
        oneline = bool(RE_BIOCLINICA_ONELINE.search(cand)) if cand else False
        param = _este_linie_parametru(cand) if cand else False
        status = "EXCLUS" if excl else ("ONELINE" if oneline else ("PARAM" if param else "skip"))
        print(f"  j={j} [{status}]: {repr(cand[:50])}")
        if not excl and cand:
            if oneline:
                print(f"  --> STOP: alta analiza completa la j={j}")
                break
            elif param:
                print(f"  --> GASIT PARAMETRU la j={j}: {repr(cand)}")
                break
            else:
                print(f"  --> skip (non-param, non-exclus, continua)")
