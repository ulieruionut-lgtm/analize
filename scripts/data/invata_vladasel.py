# -*- coding: utf-8 -*-
"""Adauga aliasuri pentru formatul Regina Maria / Vladasel - invata din buletinele existente."""
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
import psycopg2.extras

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway",
)

# (alias_raw, cod_standard) - aliasurile de adaugat pentru formatul Vladasel/Regina Maria
ALIASURI = [
    # HCT - variante OCR (1:3, 1-3)
    ("1:3 HCT% (Hematocrit)", "HCT"),
    ("1-3 HCT% (Hematocrit)", "HCT"),
    ("HCT% (Hematocrit)", "HCT"),
    # HGB - varianta cu valoare inglobata gresit
    ("1:2 HGB (Hemoglobina) 13.2", "HB"),
    # Urina - prefix numeric 1.1.x, 1.2.x
    ("1.1.4 Glucoza Negativ mg/dL", "GLUCOZA_URINA"),
    ("1.1.4 Glucoza +4 mg/dL", "GLUCOZA_URINA"),
    ("Glucoza Negativ mg/dL", "GLUCOZA_URINA"),
    ("1.1.6 Bilirubina Negativ mg/dL", "BILIRUBINA_URINA"),
    ("Bilirubina Negativ mg/dL", "BILIRUBINA_URINA"),
    ("1.1.8 Nitriti Negativ mg/dL", "NITRITI"),
    ("4:18 Nitriti Negativ mg/dL", "NITRITI"),
    ("Nitriti Negativ mg/dL", "NITRITI"),
    ("1.1.10 Eritrocite Negativ ery/ul", "HEMATII_URINA"),
    ("Eritrocite Negativ ery/ul", "HEMATII_URINA"),
    ("1.1.14 * Calciu urinar", "CALCIU_URINAR"),
    ("Calciu urinar", "CALCIU_URINAR"),
    ("1.4.11 * Acid ascorbic Negativ mg/dL", "ACID_ASCORBIC_URINA"),
    ("$.1.11 * Acid ascorbic Negativ mg/dL", "ACID_ASCORBIC_URINA"),
    ("1.1.11 * Acid ascorbic Negativ mg/dL", "ACID_ASCORBIC_URINA"),
    ("* Acid ascorbic Negativ mg/dL", "ACID_ASCORBIC_URINA"),
    ("11,13 * Microalbumina <=10 mg/L", "MICROALBUMINA"),
    ("1.1.13 * Microalbumina <=10 mg/L", "MICROALBUMINA"),
    ("* Microalbumina <=10 mg/L", "MICROALBUMINA"),
    # Sediment urinar
    ("1.2.2 Celule epiteliale tranzitionale", "CELULE_EPITELIALE_URINA"),
    ("Celule epiteliale tranzitionale", "CELULE_EPITELIALE_URINA"),
    ("1.2:3 Leucocite foarte", "LEUCOCITE_URINA"),
    ("1.2.3 Leucocite foarte", "LEUCOCITE_URINA"),
    ("Leucocite foarte", "LEUCOCITE_URINA"),
    ("1.2.4", "HEMATII_URINA"),  # Hematii sediment
    ("1.2.5 Cilindrii hialini", "CILINDRI_URINA"),
    ("4.2.5 Cilindrii hialini", "CILINDRI_URINA"),
    ("1,2:5 Cilindrii hialini", "CILINDRI_URINA"),
    ("Cilindrii hialini", "CILINDRI_URINA"),
    ("1.2.6 Cilindri patologici", "CILINDRI_URINA"),
    ("Cilindri patologici", "CILINDRI_URINA"),
    ("1.2.7 Cristale de oxalat de calciu", "CRISTALE_URINA"),
    ("ŞI Cristale de oxalat de calciu", "CRISTALE_URINA"),
    ("Cristale de oxalat de calciu", "CRISTALE_URINA"),
    ("1.2.8 Cristale acid uric", "CRISTALE_URINA"),
    ("Cristale acid uric", "CRISTALE_URINA"),
    ("1.2.9 Cristale fosfat amoniaco-magnezian", "CRISTALE_URINA"),
    ("1.2.10 Cristale amorfe", "CRISTALE_URINA"),
    ("Cristale amorfe", "CRISTALE_URINA"),
    ("1.2.11 Alte cristale", "CRISTALE_URINA"),
    ("1.2.11 Alte", "CRISTALE_URINA"),
    ("1.2.13 Levuri", "LEVURI_URINA"),
    ("Levuri", "LEVURI_URINA"),
    ("1.2.14", "MUCUS_URINA"),  # Mucus
    ("Leucocite +- leu/ul", "LEUCOCITE_URINA"),
]

# Coduri care ar putea lipsi - le cream daca nu exista
CODURI_OPȚIONALE = {
    "CALCIU_URINAR": "Calciu urinar",
    "ACID_ASCORBIC_URINA": "Acid ascorbic urina",
    "CELULE_EPITELIALE_URINA": "Celule epiteliale tranzitionale urina",
    "LEVURI_URINA": "Levuri urina",
    "NITRITI": "Nitriti urina",
    "MICROALBUMINA": "Microalbumina urinara",
}


def get_std_id(cur, cod: str) -> int | None:
    cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = %s", (cod,))
    r = cur.fetchone()
    return r["id"] if r else None


def ensure_std(cur, cod: str, denumire: str) -> int:
    cur.execute(
        "INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES (%s, %s) ON CONFLICT (cod_standard) DO NOTHING",
        (cod, denumire),
    )
    cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = %s", (cod,))
    return cur.fetchone()["id"]


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Creeaza analize standard care lipsesc
    for cod, denumire in CODURI_OPȚIONALE.items():
        if get_std_id(cur, cod) is None:
            ensure_std(cur, cod, denumire)
            print(f"  + analiza_standard: {cod} = {denumire}")

    adaugate = 0
    sarite = 0
    erori = 0

    for alias_raw, cod in ALIASURI:
        std_id = get_std_id(cur, cod)
        if std_id is None:
            print(f"  SKIP: cod {cod} nu exista - alias '{alias_raw[:50]}...'")
            sarite += 1
            continue
        try:
            cur.execute(
                """
                INSERT INTO analiza_alias (analiza_standard_id, alias)
                VALUES (%s, %s)
                ON CONFLICT (alias) DO NOTHING
                """,
                (std_id, alias_raw.strip()),
            )
            if cur.rowcount > 0:
                adaugate += 1
                print(f"  + {cod}: '{alias_raw[:55]}{'...' if len(alias_raw)>55 else ''}'")
            else:
                sarite += 1
        except Exception as e:
            erori += 1
            print(f"  ERR '{alias_raw[:40]}': {e}")

    conn.commit()
    print(f"\n=== GATA ===")
    print(f"  Adaugate: {adaugate}, Sarite (existent): {sarite}, Erori: {erori}")
    conn.close()


if __name__ == "__main__":
    main()
