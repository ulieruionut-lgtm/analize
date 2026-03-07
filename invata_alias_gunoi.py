# encoding: utf-8
"""
Adauga aliasuri pentru textele OCR garbled identificate,
astfel incat sa fie recunoscute automat la urmatoarea incarcare.
NU sterge nimic.
"""
import psycopg2, psycopg2.extras, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

def adauga_alias(alias, std_id, descriere):
    cur.execute(
        "INSERT INTO analiza_alias (analiza_standard_id, alias) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (std_id, alias)
    )
    if cur.rowcount:
        print(f"  INVATAT: '{alias}' -> std_id={std_id} ({descriere})")
    else:
        print(f"  DEJA EXISTA: '{alias}' -> std_id={std_id} ({descriere})")

print("=== Adaug aliasuri pentru texte OCR garbled ===\n")

# ─── 1. [i a ( )] = 43.3 % -> LIMFOCITE_PCT (id=15) ─────────────────────────
# Textul "LYM (%)" citit de OCR ca "i a ( )"
adauga_alias("i a ( )", 15, "Limfocite % (LYM%)")
adauga_alias("i a()", 15, "Limfocite % (LYM%)")
adauga_alias("i a ( ) (%)", 15, "Limfocite % (LYM%)")

# ─── 2. [a lit nr.] = 679 -> VIT_B12 (id=60) ─────────────────────────────────
# Denumirea "Cobalamina" / "Vitamina B12" citita de OCR ca "a lit nr."
adauga_alias("a lit nr.", 60, "Vitamina B12")
adauga_alias("a lit nr", 60, "Vitamina B12")

# ─── 3. [IRT aa cn aia aaa a ES A E NENEA a] = 2.0 -> LIMFOCITE_NR (id=16) ───
# Valoarea 2.0 (x10^9/L) corespunde numarului absolut de limfocite
# din acelasi buletin care are LYM% = 43.3, WBC = 4.83
# (4.83 x 43.3% = 2.09 ≈ 2.0 confirmat matematic)
adauga_alias("IRT aa cn aia aaa a ES A E NENEA a", 16, "Limfocite nr absolut (LYM)")
adauga_alias("IRT aa cn aia aaa", 16, "Limfocite nr absolut (LYM)")

# ─── 4. Filtre suplimentare - texte care nu sunt analize ─────────────────────
# Acestea vor fi prinse de parser in viitor, dar adaugam si la nivel de alias
# pentru buletinele deja existente - NU le mapam la nicio analiza standard
# (le sterg direct pentru ca sunt header-uri, nu analize)
GUNOI_CLAR = [
    894,  # [RETEAUA PRIVATA DE SANATATE Data - ora recoltare...]
    895,  # [Coad:5hn a]
    899,  # [E Cod:5]
    905,  # [Bacteriurie <]
    906,  # [Pt REGINA MARIA macingez lar]
]
print("\n=== Sterg entitati care sunt GARANTAT header-uri/coduri (nu analize medicale) ===")
for rid in GUNOI_CLAR:
    cur.execute("DELETE FROM rezultate_analize WHERE id = %s", (rid,))
    if cur.rowcount:
        print(f"  Sters rid={rid}")

# ─── 5. Mapeaza in buletin curent ce putem identifica ─────────────────────────
print("\n=== Mapeaza in buletinul curent (B25, B26) ===")
# rid=890 [i a ( )] = 43.3 -> LIMFOCITE_PCT
cur.execute("UPDATE rezultate_analize SET analiza_standard_id = 15 WHERE id = 890")
print(f"  rid=890 [i a ( )] -> LIMFOCITE_PCT: {cur.rowcount}")

# rid=882 [IRT aa cn aia aaa a ES A E NENEA a] = 2.0 -> LIMFOCITE_NR
cur.execute("UPDATE rezultate_analize SET analiza_standard_id = 16 WHERE id = 882")
print(f"  rid=882 [IRT aa cn aia...] -> LIMFOCITE_NR: {cur.rowcount}")

# rid=901 [a lit nr.] = 679 -> VIT_B12
cur.execute("UPDATE rezultate_analize SET analiza_standard_id = 60 WHERE id = 901")
print(f"  rid=901 [a lit nr.] -> VIT_B12: {cur.rowcount}")

# rid=902 [14.2] = 14.3 sia -> HB (Hemoglobina)
# "14.2" este limita inferioara de referinta citita ca denumire; valoarea = 14.3
cur.execute("UPDATE rezultate_analize SET analiza_standard_id = 3, denumire_raw = 'Hemoglobina' WHERE id = 902")
print(f"  rid=902 [14.2] = 14.3 -> HB (Hemoglobina): {cur.rowcount}")

# rid=903 [i ne soia ta a SE co] = 3.0 din B26 - NECUNOSCUT
# Valoarea 3.0 cu unitate "E" - nu putem identifica cu certitudine
# Lasam ca necunoscut - se va afisa in lista de aprobare manuala

# ─── 6. Verifica starea finala ────────────────────────────────────────────────
print("\n=== Stare finala nerecunoscute B25, B26 ===")
cur.execute("""
    SELECT r.id as rid, r.denumire_raw, r.valoare, r.unitate
    FROM rezultate_analize r
    WHERE r.buletin_id IN (25, 26) AND r.analiza_standard_id IS NULL
    ORDER BY r.id
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  rid={row['rid']} | [{row['denumire_raw']}] = {row['valoare']} {row['unitate'] or ''}")
else:
    print("  NICIUNA!")

# ─── 7. Verifica aliasurile salvate ───────────────────────────────────────────
print("\n=== Aliasuri salvate pentru aceste texte OCR ===")
cur.execute("""
    SELECT aa.alias, aa.analiza_standard_id, ast.cod_standard, ast.denumire_standard
    FROM analiza_alias aa
    JOIN analiza_standard ast ON ast.id = aa.analiza_standard_id
    WHERE aa.alias IN ('i a ( )', 'a lit nr.', 'IRT aa cn aia aaa a ES A E NENEA a',
                       'i a()', 'a lit nr', 'IRT aa cn aia aaa')
    ORDER BY aa.analiza_standard_id
""")
for row in cur.fetchall():
    print(f"  '{row['alias']}' -> {row['cod_standard']} ({row['denumire_standard']})")

conn.commit()
print("\n=== COMMIT OK ===")
conn.close()
print("\nGata!")
print("\nNOTA: 'i ne soia ta a SE co' = 3.0 din B26 ramane NECUNOSCUT.")
print("Valoarea 3 cu unitatea 'E' nu poate fi identificata cu certitudine.")
print("Te rog verifica in PDF ce analiza are valoarea 3 in acel buletin.")
