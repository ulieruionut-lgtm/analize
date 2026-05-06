# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pdfplumber

path = r'c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\a204ebdd-e453-416b-b7ce-a660fb82f24b\buletin analize 13.02.2026.pdf'

with pdfplumber.open(path) as pdf:
    for i, page in enumerate(pdf.pages):
        t = page.extract_text()
        if t:
            print(f'=== Pagina {i+1} ===')
            print(t)
            print()
