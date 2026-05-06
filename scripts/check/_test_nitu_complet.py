"""
Test COMPLET - simuleaza exact ce face Railway pe PDF-ul Nitu Matei.
Foloseste pdfplumber (la fel ca backend-ul pe Railway).
"""
import sys, re, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"d:\Ionut analize")

import pdfplumber

PDF_PATH = r"c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\1c519765-1585-4cfd-96c0-93bed9dae410\buletin analize 13.02.2026.pdf"

# ─── Citire PDF cu pdfplumber ───────────────────────────────────────
print("=" * 70)
print("CITIRE PDF CU PDFPLUMBER")
print("=" * 70)

all_text = ""
with pdfplumber.open(PDF_PATH) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        txt = page.extract_text() or ""
        print(f"\n--- PAGINA {page_num} ({len(txt)} chars) ---")
        print(txt[:3000] if len(txt) > 3000 else txt)
        all_text += "\n" + txt

print("\n\n" + "=" * 70)
print("TEXT COMPLET LINII NUMEROTATE")
print("=" * 70)
lines_raw = [l.strip() for l in all_text.replace("\r", "\n").split("\n")]
for i, l in enumerate(lines_raw):
    if l:
        print(f"{i:4d}: {repr(l)}")

# ─── Ruleaza parserul ───────────────────────────────────────────────
print("\n\n" + "=" * 70)
print("REZULTATE PARSER")
print("=" * 70)
from backend.parser import extract_rezultate, extract_cnp, extract_nume, _combina_linii_bioclinica, _LINII_EXCLUSE

cnp = extract_cnp(all_text)
print(f"CNP gasit: {cnp}")
nume, prenume = extract_nume(all_text)
print(f"Nume: {nume} | Prenume: {prenume}")

# Debug combina_linii
print("\n--- Linii DUPA combinare Bioclinica ---")
lines_combinate = _combina_linii_bioclinica(lines_raw)
for i, l in enumerate(lines_combinate):
    if l:
        print(f"{i:4d}: {repr(l)}")

results = extract_rezultate(all_text)
print(f"\nTotal analize gasite: {len(results)}")
print()
for r in results:
    flag = f" [{r.flag}]" if r.flag else ""
    interval = f" ({r.interval_min} - {r.interval_max})" if r.interval_min is not None else ""
    print(f"  ✓ {r.denumire_raw:<40} = {r.valoare} {r.unitate or ''}{interval}{flag}")

# ─── Verifica ce lipseste din cele 24 asteptate ─────────────────────
print("\n\n" + "=" * 70)
print("VERIFICARE ANALIZE ASTEPTATE vs GASITE")
print("=" * 70)
ASTEPTATE = [
    "Hematii", "Hemoglobina", "Hematocrit", "MCV", "MCH", "MCHC", "RDW",
    "Trombocite", "Leucocite",
    "Neutrofile", "Neutrofile %", "Limfocite", "Limfocite %",
    "Monocite", "Monocite %", "Eozinofile", "Eozinofile %",
    "Bazofile", "Bazofile %",
    "Proteina C reactiva",
    "TGO", "TGP", "Creatinina",
]

gasite_raw = [r.denumire_raw.lower() for r in results]
for a in ASTEPTATE:
    found = any(a.lower() in g for g in gasite_raw)
    status = "✓" if found else "✗ LIPSESTE"
    print(f"  {status:<12} {a}")

print("\n--- Linii EXCLUSE din PDF ---")
for l in lines_combinate:
    if l and _LINII_EXCLUSE.match(l):
        print(f"  EXCLUS: {repr(l)}")
