# -*- coding: utf-8 -*-
import sys, io, fitz
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

path = r'e:\AI\Analize cloude\Ionut analize\Ionut analize\samples\golden_pdfs\Pivets Nicile.pdf'

doc = fitz.open(path)
for i, page in enumerate(doc):
    t = page.get_text()
    if t.strip():
        print(f"=== Pagina {i+1} RAW ===")
        lines = t.split('\n')
        for j, l in enumerate(lines):
            print(f"{j:3d}: {repr(l)}")
        print()
doc.close()
