"""Adauga alias-uri pentru variatiile OCR gasite la Laza (umar->Numar, truncari, artefacte).
Ruleaza o singura data - ON CONFLICT DO NOTHING."""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway",
)

import psycopg2

# (alias_raw, cod_standard) - variatii OCR din buletinele Laza 45, 46
ALIAS_OCR = [
    ("umar de eozinofile", "EOZINOFILE_NR"),
    ("umar de eozinofile (EOS)", "EOZINOFILE_NR"),
    ("umar de neutrofile", "NEUTROFILE_NR"),
    ("umar de neutrofile (NEUT)", "NEUTROFILE_NR"),
    ("umar de neutrofile (NEUT) :", "NEUTROFILE_NR"),
    ("Numar de neutrofile (NEUT) :", "NEUTROFILE_NR"),
    ("umar de bazofile", "BAZOFILE_NR"),
    ("umar de limfocite", "LIMFOCITE_NR"),
    ("umar de monocite", "MONOCITE_NR"),
    ("umar de trombocite", "PLT"),
    ("umar de eritrocite", "RBC"),
    ("umar de leucocite", "WBC"),
    # Truncari RDW
    ("Largimea distributiei eritrocitare - coe", "RDW"),
    ("Largimea distributiei eritrocitare - coeficient", "RDW"),
    # Truncari PDW
    ("Distributia plachetelor(trombocitelor) (", "PDW"),
]


def main():
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    cur = conn.cursor()

    adaugate = 0
    for alias, cod in ALIAS_OCR:
        try:
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
                print(f"  + '{alias}' -> {cod}")
        except Exception as e:
            print(f"  ERR '{alias}': {e}")

    conn.commit()
    conn.close()
    print(f"\nAdaugate: {adaugate} alias-uri OCR. Restul existau deja.")


if __name__ == "__main__":
    main()
