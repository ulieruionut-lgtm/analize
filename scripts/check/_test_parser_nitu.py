# -*- coding: utf-8 -*-
"""Simuleaza parserul backend pe PDF-ul Nitu pentru a vedea ce se extrage."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Evitam importul complet al config-ului cu pydantic
os.environ.setdefault("DATABASE_URL", "sqlite")
os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("ADMIN_PASSWORD", "test")

from parser import extrage_date_buletin

pdf_path = r'c:\Users\User\AppData\Roaming\Cursor\User\workspaceStorage\a64a59466674168dda6d913f39f0e1ac\pdfs\a204ebdd-e453-416b-b7ce-a660fb82f24b\buletin analize 13.02.2026.pdf'

print(f"Parsez: {pdf_path}\n")
try:
    result = extrage_date_buletin(pdf_path)
    print(f"CNP: {result.get('cnp')}")
    print(f"Nume: {result.get('nume')}")
    print(f"Prenume: {result.get('prenume')}")
    print(f"Data recoltare: {result.get('data_recoltare')}")
    print(f"Laborator: {result.get('laborator')}")
    print(f"\nAnalize extrase ({len(result.get('analize', []))}):")
    for a in result.get('analize', []):
        print(f"  {a.get('denumire')} = {a.get('valoare')} {a.get('unitate', '')}")
except Exception as e:
    import traceback
    print(f"EROARE: {e}")
    traceback.print_exc()
