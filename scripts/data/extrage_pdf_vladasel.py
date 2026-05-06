"""Extrage text din PDF-uri Vladasel - standalone fara backend."""
import sys
from pathlib import Path

p1 = Path(r"C:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\3a221403-54a0-4cdc-bf7c-a9878caf83e7\buletin analize 22.12.2025 ....pdf")
p2 = Path(r"C:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\58b59afb-a62e-48a0-a717-47fb324bf9b7\buletin analize 22.12.2025.pdf")

def extract_with_pdfplumber(path):
    import pdfplumber
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            t = page.extract_text()
            if t:
                text_parts.append(t)
            # Tabele
            for tbl in page.extract_tables() or []:
                for row in tbl:
                    if any(c for c in row):
                        text_parts.append("  ".join(str(c or "").strip() for c in row))
    return "\n".join(text_parts)

def run(pdf_path, out_name):
    if not pdf_path.exists():
        print(f"NU EXISTA: {pdf_path}")
        return
    text = extract_with_pdfplumber(pdf_path)
    out = Path(__file__).parent / f"extract_{out_name}.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Scris: {out} ({len(text)} chars)")

run(p1, "vladasel_1.txt")
run(p2, "vladasel_2.txt")
