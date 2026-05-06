"""
Curata gunoi OCR din buletinele Laza (ID 20 si 21).
- Sterge duplicate (buletin 21 = copie exacta a buletin 20)
- Sterge toate intrarile cu denumire_raw = gunoi OCR
- Corecteaza MPV (99.0 -> 9.9)
- Mapeaza analizele nerecunoscute catre analiza_standard corecte
"""
import os, sys

import psycopg2
import psycopg2.extras

PUBLIC_DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
db_url = os.environ.get("DATABASE_URL", PUBLIC_DB_URL)
conn = psycopg2.connect(db_url)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ─── 1. Sterge buletin 21 (duplicat exact al buletin 20) ─────────────────────
print("=== Sterg buletin ID=21 (duplicat) ===")
cur.execute("DELETE FROM rezultate_analize WHERE buletin_id = 21")
print(f"  Sterse {cur.rowcount} rezultate din buletin 21")
cur.execute("DELETE FROM buletine WHERE id = 21")
print(f"  Buletin 21 sters: {cur.rowcount}")

# ─── 2. Sterge intrarile gunoi din buletin 20 ─────────────────────────────────
RID_GUNOI = [
    670,  # [ðST Sie ie e]
    688,  # [Cca aa aaa E O SI A RA e Spezia]
    689,  # [i CR CE SERE De E Oa nea Cai ca ei a a ea Mac Saci]
    690,  # [c□ db Ea lua]
    691,  # [Fo e BE II SE PN SR pe POS De Aaaa ... ]
    693,  # [> bose aport ce aie A ae et apa Re ae]
    699,  # [pa creme cate ate sa e at e REED aa RI RR A]
    700,  # [eGFR: 2]       <- interval de referinta, nu valoare
    701,  # [eGFR: 60 -]    <- interval de referinta
    704,  # [crescute 2]    <- eticheta
    705,  # [pana e a aa E N ON NNE N e N NR N RI N a]
    709,  # [pc aaa o as E]
    711,  # [a on anna amara E DEEE ORE OR A OS a O a a N RR Ia aaa]
    728,  # [Laza Ana Ramona A]   <- numele pacientei
    729,  # [S ic]
    730,  # [1.87]
    731,  # [o aaa aaa taia ta]
]

print(f"\n=== Sterg {len(RID_GUNOI)} intrari gunoi din buletin 20 ===")
for rid in RID_GUNOI:
    cur.execute("DELETE FROM rezultate_analize WHERE id = %s", (rid,))
    if cur.rowcount:
        print(f"  Sters rid={rid}")
    else:
        print(f"  rid={rid} deja absent")

# ─── 3. Corecteaza MPV 99.0 → 9.9 in buletin 20 ────────────────────────────
print("\n=== Corectez MPV 99.0 -> 9.9 in buletin 20 ===")
cur.execute("UPDATE rezultate_analize SET valoare = 9.9 WHERE id = 686")
print(f"  Updated: {cur.rowcount} randuri")

# ─── 4. Vizualizeaza analizele_standard disponibile ──────────────────────────
print("\n=== Analize standard disponibile ===")
cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard ORDER BY id")
std_rows = cur.fetchall()
std_by_cod = {}
for row in std_rows:
    print(f"  id={row['id']} cod={row['cod_standard']} | {row['denumire_standard']}")
    if row['cod_standard']:
        std_by_cod[row['cod_standard']] = row['id']

# ─── 5. Mapeaza analizele nerecunoscute ──────────────────────────────────────
print("\n=== Intrari nerecunoscute ramase in buletin 20 ===")
cur.execute("""
    SELECT id, denumire_raw, valoare
    FROM rezultate_analize
    WHERE buletin_id = 20 AND analiza_standard_id IS NULL
    ORDER BY id
""")
nerecunoscute = cur.fetchall()
for r in nerecunoscute:
    print(f"  rid={r['id']} | [{r['denumire_raw']}] = {r['valoare']}")

# Mapeaza analizele cunoscute manual
MAPARI = {
    694: None,   # [_ ASPARTATAMINOTRANSFERAZA (GOT/AST/TG0)] - cauta std_id AST
}

# Cauta std_id pentru AST
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard ILIKE 'AST' OR denumire_standard ILIKE '%%aspartat%%'")
row = cur.fetchone()
ast_id = row['id'] if row else None
print(f"\n  AST std_id = {ast_id}")

# Cauta std_id pentru Vitamina D (25-OH)
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard ILIKE 'VIT_D' OR denumire_standard ILIKE '%%vitamina d%%' OR denumire_standard ILIKE '%%25-oh%%'")
row = cur.fetchone()
vitd_id = row['id'] if row else None
print(f"  Vitamina D std_id = {vitd_id}")

# Cauta std_id pentru Sodiu
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard ILIKE 'Na' OR denumire_standard ILIKE '%%sodiu%%'")
row = cur.fetchone()
sodiu_id = row['id'] if row else None
print(f"  Sodiu std_id = {sodiu_id}")

# Cauta std_id pentru FT4 (Tiroxina libera)
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard ILIKE 'FT4' OR denumire_standard ILIKE '%%tiroxina%%' OR denumire_standard ILIKE '%%ft4%%'")
row = cur.fetchone()
ft4_id = row['id'] if row else None
print(f"  FT4 std_id = {ft4_id}")

print("\n=== Mapeaza analizele recunoscute ===")
# _ ASPARTATAMINOTRANSFERAZA -> AST
if ast_id:
    cur.execute(
        "UPDATE rezultate_analize SET analiza_standard_id = %s WHERE id = 694",
        (ast_id,)
    )
    print(f"  rid=694 [_ ASPARTATAMINOTRANSFERAZA] -> std_id={ast_id}: {cur.rowcount} updated")

# 25-0H-VITAMINA D -> VIT_D
if vitd_id:
    cur.execute(
        "UPDATE rezultate_analize SET analiza_standard_id = %s WHERE id = 718",
        (vitd_id,)
    )
    print(f"  rid=718 [25-0H-VITAMINA D] -> std_id={vitd_id}: {cur.rowcount} updated")

# SODIU SERIC -> Na
if sodiu_id:
    cur.execute(
        "UPDATE rezultate_analize SET analiza_standard_id = %s WHERE id = 710",
        (sodiu_id,)
    )
    print(f"  rid=710 [SODIU SERIC] -> std_id={sodiu_id}: {cur.rowcount} updated")

# FTA (TIROXINA LIBERA) -> FT4
if ft4_id:
    cur.execute(
        "UPDATE rezultate_analize SET analiza_standard_id = %s WHERE id = 723",
        (ft4_id,)
    )
    print(f"  rid=723 [FTA (TIROXINA LIBERA)] -> std_id={ft4_id}: {cur.rowcount} updated")

# ─── 6. Adauga aliasuri pentru recunoastere viitoare ─────────────────────────
print("\n=== Adauga aliasuri pentru recunoastere viitoare ===")
ALIASURI = []
if ast_id:
    ALIASURI.append(("_ ASPARTATAMINOTRANSFERAZA (GOT/AST/TG0)", ast_id))
    ALIASURI.append(("ASPARTATAMINOTRANSFERAZA (GOT/AST/TG0)", ast_id))
if vitd_id:
    ALIASURI.append(("25-0H-VITAMINA D *", vitd_id))
    ALIASURI.append(("25-OH-VITAMINA D", vitd_id))
if sodiu_id:
    ALIASURI.append(("SODIU SERIC", sodiu_id))
if ft4_id:
    ALIASURI.append(("FTA (TIROXINA LIBERA)", ft4_id))
    ALIASURI.append(("FT4 TIROXINA LIBERA", ft4_id))

for alias, std_id in ALIASURI:
    try:
        cur.execute(
            "INSERT INTO analiza_alias (analiza_standard_id, alias) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (std_id, alias)
        )
        print(f"  Alias adaugat: '{alias}' -> std_id={std_id}")
    except Exception as e:
        print(f"  Eroare alias '{alias}': {e}")

# ─── 7. Verifica ce mai ramane nerecunoscut ───────────────────────────────────
print("\n=== Intrari finale nerecunoscute in buletin 20 ===")
cur.execute("""
    SELECT id, denumire_raw, valoare
    FROM rezultate_analize
    WHERE buletin_id = 20 AND analiza_standard_id IS NULL
    ORDER BY id
""")
for r in cur.fetchall():
    print(f"  rid={r['id']} | [{r['denumire_raw']}] = {r['valoare']}")

conn.commit()
print("\n=== COMMIT OK ===")
cur.close()
conn.close()
print("Gata!")
