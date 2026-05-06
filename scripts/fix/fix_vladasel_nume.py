# encoding: utf-8
"""Corecteaza numele pacientului Vladasel Elena in DB.
Ruleaza (cu venv activ si DATABASE_URL setat):
  python fix_vladasel_nume.py
  # sau pe Railway: railway run python fix_vladasel_nume.py

Alternativ: din aplicatie, tab Setari (admin) -> buton "Corectează nume (Vladasel etc.)"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from backend.database import fix_pacienti_nume_cunoscuti

    corectati = fix_pacienti_nume_cunoscuti()
    for c in corectati:
        print(f"  {c['cnp']}: nume='{c['nume']}' prenume='{c['prenume']}'")
    print(f"OK - {len(corectati)} pacienti corectati. Numele nu vor mai fi suprascrise la upload.")


if __name__ == "__main__":
    main()
