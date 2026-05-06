# -*- coding: utf-8 -*-
"""Debug de ce TGO nu e gasit."""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Reutilizeaza definitiile din test anterior
exec(open('_test_parser_simulare.py', encoding='utf-8').read().split('=== Simulare')[0])

# Reconstruieste liniile combinate din textul complet
import fitz
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

# Gaseste indexul lui "74 U/L (9 - 80)"
for i, l in enumerate(lines):
    if '74' in l and 'U/L' in l:
        print(f"Linia {i}: {l!r}")
        # Cauta TGO inapoi
        for j in range(i-1, max(i-35, -1), -1):
            cand = lines[j]
            excl = bool(_LINII_EXCLUSE.match(cand)) if cand else True
            oneline = bool(RE_BIOCLINICA_ONELINE.search(cand)) if cand else False
            param = _este_linie_parametru(cand) if cand else False
            print(f"  j={j}: excl={excl} oneline={oneline} param={param} | {repr(cand)[:60]}")
        break
