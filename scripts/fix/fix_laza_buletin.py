"""
Script de corectie date gresite pentru Laza - buletin 05.12.2025 (buletin_id=4).
Ruleaza cu: railway run python fix_laza_buletin.py
"""
import os, sys
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

url = os.environ.get("DATABASE_URL", "").strip()
if not url or not url.lower().startswith("postgres"):
    print("EROARE: DATABASE_URL nu e setat.")
    sys.exit(1)

import psycopg2
conn = psycopg2.connect(url)
conn.autocommit = False
cur = conn.cursor()

print("=== Corectie date Laza buletin_id=4 ===\n")

# 1. Corecteaza mapari gresite (UPDATE analiza_standard_id)
fixes = [
    # (buletin_rezultat_id, cod_standard_corect, descriere)
    (58,  'RBC',           'Numar de eritrocite (RBC)'),
    (64,  'EOZINOFILE_PCT','Procentul de eozinofile (EOS%)'),
    (68,  'NEUTROFILE_NR', 'Numar de neutrofile (NEUT)'),
    (69,  'EOZINOFILE_NR', 'Numar de eozinofile (EOS)'),
    (70,  'BAZOFILE_NR',   'Numar de bazofile (BAS)'),
    (71,  'MONOCITE_NR',   'Numar de monocite (MON)'),
    (72,  'PLT',           'Numar de trombocite (PLT)'),
    (74,  'PDW',           'Distributia plachetelor (PDW-SD)'),
    (73,  'MPV',           'Volumul mediu plachetar (MPV)'),
    (105, 'VIT_B12',       'VITAMINA B12'),
    (111, 'ASLO',          'ANTICORPI ANTI-STREPTOLIZINA O (ASLO)'),
    (75,  'ALT',           'ALANINAMINOTRANSFERAZA (ALT/GPT/TGP)'),
    (76,  'AST',           'ASPARTATAMINOTRANSFERAZA (GOT/AST/TGO)'),
    (112, 'FR',            'FACTOR REUMATOID'),
    (113, 'IGE',           'IgE (IMUNOGLOBULINA E)'),
    (128, 'COMPLEMENT_C3', 'COMPLEMENT C3'),
    (129, 'DAO',           'DIAMINOXIDAZA (DAO)'),
    (130, 'PTH',           'iPTH (PARATHORMON INTACT)'),
    (420, 'LIMFOCITE_NR',  'Numar de limfocite (LYM)'),
]

for rez_id, cod, desc in fixes:
    cur.execute("""
        UPDATE rezultate_analize
        SET analiza_standard_id = (SELECT id FROM analiza_standard WHERE cod_standard=%s)
        WHERE id=%s
        AND (SELECT id FROM analiza_standard WHERE cod_standard=%s) IS NOT NULL
    """, (cod, rez_id, cod))
    if cur.rowcount > 0:
        print(f"  UPDATE id={rez_id}: {desc} -> {cod}")
    else:
        print(f"  SKIP   id={rez_id}: {desc} (nu exista sau cod_standard '{cod}' negasit)")

# 2. Sterge liniile gunoi (note/clasificari extrase gresit ca analize)
garbage_ids = [
    79,   # "Usor crescut : 100 -"
    80,   # "Moderat crescut : 130 -"
    81,   # "Crescut : 160 -"
    82,   # "Foarte crescut: >"
    83,   # "Acceptabil: <"
    84,   # "Borderline crescut : 120 -"
    85,   # "Crescut : >"
    86,   # "Foarte crescut: 2"
    88,   # "eGFR: ="
    89,   # "eGFR: 60 -"
    90,   # "eGFR: <"
    91,   # "persoane varstince - eGRF: <"
    92,   # "eGFR ="
    93,   # "k ="
    94,   # "persoanelor peste 16 ani..."
    96,   # "Normal: 60 -"
    97,   # "Glicemie bazala modificata: 100 -"
    98,   # "Diagnosticul de diabet..."
    99,   # "crescute >"
    103,  # "PD"
    109,  # "Deficit foarte sever: <"
    110,  # "Nivel toxic: >"
    117,  # "trimestrul | 10.7 -"
    118,  # "20-40 ani : 12.4 -"
    120,  # "trimester | 0.10 -"
    121,  # "trimester II 0.20 -"
    122,  # "trimester III 0.3 -"
    123,  # "20-40 ani : 0.52 -"
    124,  # "peste 40 ani: 0.3 -"
    125,  # "Regulamentul nr."
    126,  # ": s i"
    127,  # "Se recomanda retestare..."
    131,  # "E e"
    132,  # "i Ea a acte o oa a"
    133,  # "o A"
]

cur.execute(
    "DELETE FROM rezultate_analize WHERE id = ANY(%s)",
    (garbage_ids,)
)
print(f"\n  DELETE: {cur.rowcount} randuri gunoi sterse din buletin_id=4")

# 3. Corecteaza valoarea MPV: 99.0 → 9.9 (OCR a citit '9.9 fL' ca '99 f..')
cur.execute("""
    UPDATE rezultate_analize
    SET valoare=9.9, unitate='fL', flag=NULL
    WHERE id=73
""")
if cur.rowcount > 0:
    print("\n  FIX MPV: valoare 99.0 -> 9.9 fL")

conn.commit()
cur.close()
conn.close()
print("\n=== Corectie finalizata! ===")
