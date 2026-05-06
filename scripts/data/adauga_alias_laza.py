"""Adauga alias-uri pentru variatiile OCR gasite la Laza (umar->Numar, RDW CV, etc)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URL", (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
))

# (alias_raw, cod_standard)
ALIASURI_LAZA = [
    # OCR: "umar" citit gresit ca "Numar"
    ("umar de eozinofile (EOS)", "EOZINOFILE_NR"),
    ("umar de neutrofile (NEUT)", "NEUTROFILE_NR"),
    ("umar de neutrofile (NEUT) :", "NEUTROFILE_NR"),
    ("Numar de neutrofile (NEUT) :", "NEUTROFILE_NR"),
    # RDW - variatie fara cratima
    ("Largimea distributiei eritrocitare - coeficient variatie (RDW CV)", "RDW"),
    ("Largimea distributiei eritrocitare - coeficient variatie (RDW-CV)", "RDW"),
    # Homocisteina cu asterisc
    ("HOMOCISTEINA *", "HOMOCIST"),
    ("Homocisteina *", "HOMOCIST"),
    # Fier seric cu artefact OCR in paranteze
    ("FIER SERIC (SIDEREMIE) [197.52 wo/a]", "FIER"),
    ("FIER SERIC (SIDEREMIE)", "FIER"),
    # Indice distributie trombocite - variatii
    ("PDW – Indice distributie trombocite", "PDW"),
    ("Indice distributie trombocite", "PDW"),
]


def main():
    import psycopg2

    db_url = os.environ.get("DATABASE_URL")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    adaugate = 0
    for alias, cod in ALIASURI_LAZA:
        cur.execute(
            """
            INSERT INTO analiza_alias (analiza_standard_id, alias)
            SELECT a.id, %s FROM analiza_standard a WHERE a.cod_standard = %s
            ON CONFLICT (alias) DO NOTHING
            """,
            (alias.strip(), cod),
        )
        if cur.rowcount > 0:
            adaugate += 1
            print(f"  + '{alias[:50]}...' -> {cod}" if len(alias) > 50 else f"  + '{alias}' -> {cod}")

    conn.commit()
    print(f"\nAdaugate {adaugate} alias-uri noi. Restul existau deja.")
    conn.close()


if __name__ == "__main__":
    main()
