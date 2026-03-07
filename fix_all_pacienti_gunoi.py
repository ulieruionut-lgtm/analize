# encoding: utf-8
import psycopg2, psycopg2.extras, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ─── B6 (Iancu Gheorghe) ──────────────────────────────────────────────────────
print("=== B6 Iancu Gheorghe ===")

# rid=151 [- eGFR*] = 62.77 -> EGFR (std_id=37)
cur.execute("UPDATE rezultate_analize SET analiza_standard_id = 37, denumire_raw = 'eGFR' WHERE id = 151")
print(f"  rid=151 [- eGFR*] -> EGFR: {cur.rowcount}")

# rid=139 [Globuline beta po] = 2.0 - numar fragmentat, DELETE
cur.execute("DELETE FROM rezultate_analize WHERE id = 139")
print(f"  rid=139 [Globuline beta po] sters: {cur.rowcount}")

# rid=140 [_Globuline gama %, SONS.] = 1563.0 - valoare imposibila, DELETE
cur.execute("DELETE FROM rezultate_analize WHERE id = 140")
print(f"  rid=140 [_Globuline gama %, SONS.] sters: {cur.rowcount}")

# rid=142 [_UROBILINOGEN,, Sai] = 0.2 - valoare reala, curatam denumirea
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'URINA_SUMAR' OR denumire_standard ILIKE '%%urobilinogen%%'")
row = cur.fetchone()
if row:
    cur.execute("UPDATE rezultate_analize SET analiza_standard_id = %s, denumire_raw = 'UROBILINOGEN' WHERE id = 142", (row['id'],))
    print(f"  rid=142 [_UROBILINOGEN] -> std_id={row['id']}: {cur.rowcount}")
else:
    cur.execute("DELETE FROM rezultate_analize WHERE id = 142")
    print(f"  rid=142 sters (nu exista std Urobilinogen): {cur.rowcount}")

# rid=168 [PD 1220] = 4.0 - cod partial de bare, DELETE
cur.execute("DELETE FROM rezultate_analize WHERE id = 168")
print(f"  rid=168 [PD 1220] sters: {cur.rowcount}")

# rid=170 ["Monoeite] = 680.0 - valoare imposibila pentru Monocite, DELETE
cur.execute("DELETE FROM rezultate_analize WHERE id = 170")
print(f"  rid=170 [Monoeite] sters: {cur.rowcount}")

# rid=171 [Peoznie e - a] = 40.0 - valoare imposibila, DELETE
cur.execute("DELETE FROM rezultate_analize WHERE id = 171")
print(f"  rid=171 [Peoznie e - a] sters: {cur.rowcount}")

# rid=175 [Eritroblasti E: i i] = 5.0 - analiza reala, curatam denumirea
cur.execute("SELECT id FROM analiza_standard WHERE denumire_standard ILIKE '%%eritroblast%%' OR cod_standard ILIKE 'ERITROBLASTI'")
row = cur.fetchone()
if row:
    cur.execute("UPDATE rezultate_analize SET analiza_standard_id = %s, denumire_raw = 'Eritroblasti' WHERE id = 175", (row['id'],))
    print(f"  rid=175 [Eritroblasti] -> std_id={row['id']}: {cur.rowcount}")
else:
    cur.execute("DELETE FROM rezultate_analize WHERE id = 175")
    print(f"  rid=175 sters (nu exista std Eritroblasti): {cur.rowcount}")

# ─── B7 (Benchea Petre) ───────────────────────────────────────────────────────
print("\n=== B7 Benchea Petre ===")

# rid=224 [Corpi cetonici Absenti Absenti, <] = 2.0 - referinta, DELETE
cur.execute("DELETE FROM rezultate_analize WHERE id = 224")
print(f"  rid=224 [Corpi cetonici Absenti] sters: {cur.rowcount}")

# ─── B8 (NITU MATEI) ──────────────────────────────────────────────────────────
print("\n=== B8 Nitu Matei ===")

# rid=246 [Raspuns rapid ........ < 0,4 (ziua] = 4.0 - text referinta, DELETE
cur.execute("DELETE FROM rezultate_analize WHERE id = 246")
print(f"  rid=246 [Raspuns rapid] sters: {cur.rowcount}")

# ─── B10 (VLADASEL ELENA) ─────────────────────────────────────────────────────
print("\n=== B10 Vladasel Elena ===")

# rid=267 [1 * Factor Reumatoid (FR - cantitativ) <] = 20.0
# Textul "< 20" sugereaza ca valoarea 20.0 este limita de referinta, nu valoarea reala
# Stergem - nu putem sti valoarea reala fara sa vedem buletinul original
cur.execute("DELETE FROM rezultate_analize WHERE id = 267")
print(f"  rid=267 [Factor Reumatoid] sters (valoare ambigua = limita referinta): {cur.rowcount}")

# ─── B11 (VLADASEL AUREL) ─────────────────────────────────────────────────────
print("\n=== B11 Vladasel Aurel ===")

# rid=294 [9.3 Alfa2-globuline%] = 9.9 -> ELECTRO_ALFA2 (std_id=133)
cur.execute("UPDATE rezultate_analize SET analiza_standard_id = 133, denumire_raw = 'Alfa2-globuline%' WHERE id = 294")
print(f"  rid=294 [9.3 Alfa2-globuline%] -> ELECTRO_ALFA2: {cur.rowcount}")

# rid=295 [9.4 Beta-globuline%] = 11.46 -> total beta = ELECTRO_BETA1 + ELECTRO_BETA2 cumulate
# Lasam ca ELECTRO_BETA1 (134) pentru ca e totalul
cur.execute("UPDATE rezultate_analize SET analiza_standard_id = 134, denumire_raw = 'Beta-globuline%' WHERE id = 295")
print(f"  rid=295 [9.4 Beta-globuline%] -> ELECTRO_BETA1: {cur.rowcount}")

# rid=296 [9.5 * Beta1-globuline%] = 6.16 -> ELECTRO_BETA1 (std_id=134)
cur.execute("UPDATE rezultate_analize SET analiza_standard_id = 134, denumire_raw = 'Beta1-globuline%' WHERE id = 296")
print(f"  rid=296 [9.5 Beta1-globuline%] -> ELECTRO_BETA1: {cur.rowcount}")

# rid=297 [9.6 * Beta2-globuline%] = 5.3 -> ELECTRO_BETA2 (std_id=135)
cur.execute("UPDATE rezultate_analize SET analiza_standard_id = 135, denumire_raw = 'Beta2-globuline%' WHERE id = 297")
print(f"  rid=297 [9.6 Beta2-globuline%] -> ELECTRO_BETA2: {cur.rowcount}")

# rid=298 [9.7 Gamma-globuline%] = 17.33 -> ELECTRO_GAMA (std_id=136)
cur.execute("UPDATE rezultate_analize SET analiza_standard_id = 136, denumire_raw = 'Gamma-globuline%' WHERE id = 298")
print(f"  rid=298 [9.7 Gamma-globuline%] -> ELECTRO_GAMA: {cur.rowcount}")

# ─── Adauga aliasuri pentru recunoastere viitoare ─────────────────────────────
print("\n=== Adauga aliasuri ===")
ALIASURI = [
    ("- eGFR*", 37),
    ("eGFR*", 37),
    ("Alfa2-globuline%", 133),
    ("Beta-globuline%", 134),
    ("Beta1-globuline%", 134),
    ("Beta2-globuline%", 135),
    ("Gamma-globuline%", 136),
    ("Alfa1-globuline%", 132),
    ("Alfa-globuline%", 132),
]
for alias, std_id in ALIASURI:
    try:
        cur.execute(
            "INSERT INTO analiza_alias (analiza_standard_id, alias) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (std_id, alias)
        )
        print(f"  Alias '{alias}' -> std_id={std_id}: {cur.rowcount}")
    except Exception as e:
        print(f"  Eroare alias '{alias}': {e}")

# ─── Corecteaza numele pacientilor Vladasel ───────────────────────────────────
print("\n=== Corecteaza numelor pacientilor Vladasel ===")
cur.execute("""
    UPDATE pacienti
    SET nume = 'VLADASEL ELENA', prenume = 'ELENA'
    WHERE cnp = '2470112080077'
""")
print(f"  Vladasel Elena: {cur.rowcount} updated")

cur.execute("""
    UPDATE pacienti
    SET nume = 'VLADASEL AUREL-NICOLAE-SORIN', prenume = 'AUREL-NICOLAE-SORIN'
    WHERE cnp = '1461208080072'
""")
print(f"  Vladasel Aurel: {cur.rowcount} updated")

# ─── Verifica starea finala ───────────────────────────────────────────────────
print("\n=== Stare finala - toate analizele nerecunoscute ===")
cur.execute("""
    SELECT b.id as bid, p.nume, r.id as rid, r.denumire_raw, r.valoare
    FROM rezultate_analize r
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE r.analiza_standard_id IS NULL
    ORDER BY b.id, r.id
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  B{row['bid']} ({row['nume']}) rid={row['rid']} | [{row['denumire_raw']}] = {row['valoare']}")
else:
    print("  NICIUNA! Toate analizele sunt recunoscute.")

conn.commit()
print("\n=== COMMIT OK ===")
cur.close()
conn.close()
print("Gata!")
