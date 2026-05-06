# -*- coding: utf-8 -*-
"""
Corectează aliasurile greșite adăugate de verifica_si_invata_pdf.
Rulează după ce s-a rulat verifica_si_invata_pdf cu euristici incorecte.

Utilizare: venv\\Scripts\\python.exe fix_aliasuri_gresite_invata.py [--exec]
"""
import argparse
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exec", action="store_true", help="Efectuează modificările (altfel dry-run)")
    args = parser.parse_args()

    from backend.database import get_cursor, _use_sqlite, _row_get

    ph = "?" if _use_sqlite() else "%s"

    # Mapări corecte: (alias gresit, cod_standard corect)
    CORECTARI = [
        ("Creatinină serică", "CREATININA"),
        ("Creatinina serică", "CREATININA"),
        ("Glucoză", "GLUCOZA_FASTING"),
        ("Leucocite", "WBC"),
    ]

    # Aliasuri exacte de șters (gunoi)
    STERGERI_EXACTE = [
        "Creatinină serică 10.02.2025",
        "Creatinina serică 10.02.2025",
        "Bioclinica Zărnești",
    ]
    # Pattern LIKE pentru ștergere (ex: Bioclinica Zărnești GENERAT dd.mm.yyyy hh:mm)
    STERGERI_LIKE = [
        ("Bioclinica Zărnești GENERAT%", "Bioclinica Zărnești GENERAT..."),
    ]

    with get_cursor(commit=False) as cur:
        # Obține id-urile pentru coduri corecte
        cod_to_id = {}
        for cod in ["CREATININA", "GLUCOZA_FASTING", "WBC"]:
            cur.execute(f"SELECT id FROM analiza_standard WHERE cod_standard = {ph}", (cod,))
            r = cur.fetchone()
            if r:
                cod_to_id[cod] = _row_get(r, 0 if _use_sqlite() else "id")

    if not args.exec:
        print("[DRY-RUN] Corecții și ștergeri planificate:\n")
        for alias, cod in CORECTARI:
            print(f"  UPDATE: '{alias}' -> {cod}")
        for alias in STERGERI_EXACTE:
            print(f"  DELETE: '{alias}'")
        for pat, desc in STERGERI_LIKE:
            print(f"  DELETE LIKE: {desc}")
        print("\nRulează cu --exec pentru a aplica.")
        return

    ok_upd, ok_del = 0, 0
    with get_cursor(commit=True) as cur:
        for alias, cod in CORECTARI:
            aid = cod_to_id.get(cod)
            if not aid:
                print(f"  SKIP: cod {cod} nu există")
                continue
            if _use_sqlite():
                cur.execute(
                    "UPDATE analiza_alias SET analiza_standard_id = ? WHERE LOWER(TRIM(alias)) = LOWER(TRIM(?))",
                    (aid, alias),
                )
            else:
                cur.execute(
                    "UPDATE analiza_alias SET analiza_standard_id = %s WHERE LOWER(TRIM(alias)) = LOWER(TRIM(%s))",
                    (aid, alias),
                )
            if cur.rowcount > 0:
                print(f"  ✓ '{alias}' -> {cod} (id={aid})")
                ok_upd += 1

        for alias in STERGERI_EXACTE:
            if _use_sqlite():
                cur.execute("DELETE FROM analiza_alias WHERE LOWER(TRIM(alias)) = LOWER(TRIM(?))", (alias,))
            else:
                cur.execute("DELETE FROM analiza_alias WHERE LOWER(TRIM(alias)) = LOWER(TRIM(%s))", (alias,))
            if cur.rowcount > 0:
                print(f"  ✓ Șters: '{alias}'")
                ok_del += 1

        for pat, desc in STERGERI_LIKE:
            if _use_sqlite():
                cur.execute("DELETE FROM analiza_alias WHERE alias LIKE ?", (pat,))
            else:
                cur.execute("DELETE FROM analiza_alias WHERE alias LIKE %s", (pat,))
            if cur.rowcount > 0:
                print(f"  ✓ Șters: {desc} ({cur.rowcount} intrări)")
                ok_del += cur.rowcount

    # Invalidează cache-ul normalizer
    from backend.normalizer import invalideaza_cache
    invalideaza_cache()

    print(f"\n✓ Actualizate: {ok_upd} | Șterse: {ok_del}")


if __name__ == "__main__":
    main()
