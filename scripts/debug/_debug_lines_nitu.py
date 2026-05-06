# -*- coding: utf-8 -*-
"""Verifica exact cum extrage pdfplumber textul din PDF Nitu - linie cu linie."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import fitz

path = r'c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\a204ebdd-e453-416b-b7ce-a660fb82f24b\buletin analize 13.02.2026.pdf'

doc = fitz.open(path)
all_text = ""
for i, page in enumerate(doc):
    t = page.get_text()
    if t.strip():
        all_text += t + "\n"
doc.close()

lines = all_text.split("\n")
print(f"Total linii: {len(lines)}\n")
# Afiseaza liniile cu index, focusat pe zona TGO si inceputul paginii 2
for i, l in enumerate(lines):
    print(f"{i:3d}: {repr(l)}")
