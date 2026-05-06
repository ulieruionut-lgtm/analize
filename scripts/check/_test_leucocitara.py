# -*- coding: utf-8 -*-
"""Test combinare blocuri formula leucocitara."""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

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
_LINII_EXCLUSE = re.compile(
    r"^(Hemoleucogramă|Formula\s+leucocitară|HEMOLEUCOGRAMA|BIOCHIMIE|"
    r"Pagina|CNP|ADRESA|RECOLTAT|sânge\s+integral)",
    re.IGNORECASE,
)

def _combina_linii_bioclinica(lines: list) -> list:
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

# Test cu blocul din PDF Nitu
lines_test = [
    'Leucocite',
    '3.980 /mm³',
    '(6.000 - 15.000)',
    'Formula leucocitară',
    'Neutrofile',
    '2.260 /mm³',
    '56,78 %',
    '(1.500 - 8.700)/mm³',
    '(22,00 - 63,00)%',
    'Limfocite',
    '1.150 /mm³',
    '28,89 %',
    '(3.000 - 10.000)/mm³',
    '(32,00 - 63,00)%',
    'Monocite',
    '460 /mm³',
    '11,56 %',
    '(150 - 1.200)/mm³',
    '(1,50 - 10,50)%',
]

result = _combina_linii_bioclinica(lines_test)
print("=== Dupa combinare ===")
for i, l in enumerate(result):
    print(f"  {i:2d}: {l!r}")

print("\n=== Test RE_VALOARE_LINIE ===")
for l in result:
    m = RE_VALOARE_LINIE.match(l)
    if m:
        print(f"  MATCH: {l!r} -> val={m.group(1)}, um={m.group(2).strip()}")
