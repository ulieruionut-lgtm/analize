# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import fitz  # pymupdf

path = r'c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\a204ebdd-e453-416b-b7ce-a660fb82f24b\buletin analize 13.02.2026.pdf'

doc = fitz.open(path)
for i, page in enumerate(doc):
    t = page.get_text()
    if t.strip():
        print(f'=== Pagina {i+1} ===')
        print(t)
doc.close()
