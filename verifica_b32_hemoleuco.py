import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Afiseaza tot ce e in B32
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate,
           a.denumire_standard, a.cod_standard
    FROM rezultate_analize r
    LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE r.buletin_id = 32
    ORDER BY r.id
""")
rez = cur.fetchall()
print(f"B32 - {len(rez)} rezultate:\n")
for r in rez:
    std = r['denumire_standard'] or '!!! NEMAPAT'
    val = r['valoare_text'] if r['valoare_text'] else str(r['valoare'])
    print(f"  RID={r['id']:4d} | {std:45s} | {val} {r['unitate'] or ''}")

# Verifica analiza standard pentru hemoleucograma compusa
print("\n\n=== Verificare analize standard pentru hemoleucograma ===")
analize_din_pdf = [
    "Numar leucocite", "Leucocite", "WBC",
    "Numar eritrocite", "Eritrocite", "RBC",
    "Hemoglobina", "HGB", "HB",
    "Hematocrit", "HCT",
    "VEM", "MCV", "Volum eritrocitar",
    "MCH", "HEM",
    "MCHC", "CHEM",
    "RDW-SD", "RDW-CV", "RDW",
    "Numar trombocite", "Trombocite", "PLT",
    "MPV", "VTM",
    "P-LCR", "PCT", "PDW",
    "Granulocite imature",
    "Eritroblasti",
    "P-LCR"
]

for term in set(analize_din_pdf):
    cur.execute(
        "SELECT id, cod_standard, denumire_standard FROM analiza_standard "
        "WHERE LOWER(denumire_standard) LIKE %s OR LOWER(cod_standard) LIKE %s",
        (f"%{term.lower()}%", f"%{term.lower()}%")
    )
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"  EXISTA: ID={r['id']} | {r['denumire_standard']} | cod={r['cod_standard']}")

conn.close()
