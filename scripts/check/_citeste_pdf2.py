# -*- coding: utf-8 -*-
import sys, io, fitz
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

path = r'c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\1c519765-1585-4cfd-96c0-93bed9dae410\buletin analize 13.02.2026.pdf'

doc = fitz.open(path)
all_text = ""
for i, page in enumerate(doc):
    t = page.get_text()
    if t.strip():
        print(f"=== Pagina {i+1} ===")
        print(t)
        all_text += t + "\n"
doc.close()

print("\n\n=== LINII NUMEROTATE (toate) ===")
lines = all_text.split("\n")
for i, l in enumerate(lines):
    print(f"{i:3d}: {repr(l)}")
