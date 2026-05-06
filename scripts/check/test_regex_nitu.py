# -*- coding: utf-8 -*-
"""Test doar regexurile pe text Nitu - fara backend."""
import re

# Regexuri din parser (copiate)
RE_BIOCLINICA_ONELINE = re.compile(
    r"\s+([\d.,]+)\s*([a-zA-Z0-9/%µμg·²³\u00b3\s/]+?)\s*\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)
RE_VALOARE_REF_SINGULAR = re.compile(
    r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\u00b3\s/]+?)\s*\(\s*(?:[≤≥<>]|<=|>=)\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)
_RE_FORMULA_PDFPLUMBER = re.compile(
    r"^([A-Za-zăâîșțĂÂÎȘȚ]+)\s+([\d.,]+)\s*([\/\w³·0-9]+?)\s+([\d.,]+)\s*%\s+\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)",
    re.IGNORECASE,
)
_RE_INTERVAL_PARANTEZE = re.compile(r"^\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)[^\d\n]*$")

lines = [
    "Hematii 4.650.000/mm3 (3.700.000 - 5.150.000)",
    "Hemoglobina 13,3g/dL (10,2 - 13,4)",
    "Neutrofile 2.260/mm3 56,78 % (1.500 - 8.700)/mm3",
    "(22,00 - 63,00)%",
    "2,260mg/dL (<= 0,33)",
    "74U/L (9 - 80)",
]

print("=== RE_BIOCLINICA_ONELINE (oneline hemogram) ===")
for L in lines[:2]:
    m = RE_BIOCLINICA_ONELINE.search(L)
    print(f"  {L[:60]:60} -> {'MATCH: ' + str(m.groups()) if m else 'NO'}")

print("\n=== _RE_FORMULA_PDFPLUMBER + next line ===")
for i in range(0, min(2, len(lines)-1)):
    mf = _RE_FORMULA_PDFPLUMBER.match(lines[2+i*2])
    mi = _RE_INTERVAL_PARANTEZE.match(lines[3+i*2])
    print(f"  L1: {lines[2][:50]} -> {mf.groups() if mf else 'NO'}")
    print(f"  L2: {lines[3][:30]} -> {mi.groups() if mi else 'NO'}")

print("\n=== RE_VALOARE_REF_SINGULAR (CRP) ===")
m = RE_VALOARE_REF_SINGULAR.match(lines[4])
print(f"  {lines[4]} -> {m.groups() if m else 'NO'}")

print("\n=== RE_VALOARE_LINIE (TGO 74U/L) ===")
RE_VALOARE_LINIE = re.compile(r"^([\d.,]+)\s*([a-zA-Z/%µμg·²³\s/]+?)\s*\(\s*([\d.,]+)\s*[-–]\s*([\d.,]+)\s*\)", re.IGNORECASE)
m = RE_VALOARE_LINIE.match(lines[5])
print(f"  {lines[5]} -> {m.groups() if m else 'NO'}")

print("\nDONE")
