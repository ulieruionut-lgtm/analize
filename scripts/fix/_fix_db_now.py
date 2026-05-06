import psycopg2, psycopg2.extras
DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Afiseaza starea curenta
print("=== Pacienti inainte de fix ===")
cur.execute("SELECT id, cnp, LEFT(COALESCE(nume,''),80) as nume, LEFT(COALESCE(prenume,''),40) as prenume FROM pacienti ORDER BY id")
for r in cur.fetchall():
    print(f"  [{r['id']}] {r['cnp']} | {r['nume']} | {r['prenume']}")

# Fix explicit pentru pacienti cunoscuti
FIXURI = [
    ("2470112080077", "VLADASEL", "ELENA"),
    ("1461208080072", "VLADASEL", "AUREL-NICOLAE-SORIN"),
    ("2540207080070", "PETREAN", "ANA"),
]
print("\n=== Aplicare fix ===")
for cnp, nume, prenume in FIXURI:
    cur.execute("UPDATE pacienti SET nume = %s, prenume = %s WHERE cnp = %s", (nume, prenume, cnp))
    print(f"  {cnp}: {cur.rowcount} rand(uri) actualizate -> {nume} {prenume}")

conn.commit()

# Fix general: curata orice alt pacient cu nume corupt (>80 chars sau contine 'Medic')
cur.execute("""
    UPDATE pacienti
    SET nume = TRIM(SPLIT_PART(
        REGEXP_REPLACE(
            REGEXP_REPLACE(nume, '^Nume pacient:\\s*', '', 'i'),
        '\\s+Medic\\s+trimitaro?r?.*$', '', 'i'),
        ' ', 1
    )),
    prenume = TRIM(
        SUBSTRING(
            SPLIT_PART(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(nume, '^Nume pacient:\\s*', '', 'i'),
                        '\\s+Medic\\s+trimitaro?r?.*$', '', 'i'),
                '\\s+pacient:.*$', '', 'i'),
            ' ', 1) || ' ' ||
            REGEXP_REPLACE(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(nume, '^Nume pacient:\\s*', '', 'i'),
                        '\\s+Medic\\s+trimitaro?r?.*$', '', 'i'),
                '\\s+pacient:.*$', '', 'i'),
            '^\\S+\\s*', '', 'i')
        FROM 1)
    )
    WHERE LENGTH(nume) > 40
      AND (nume ILIKE '%Medic%' OR nume ILIKE '%pacient%' OR nume ILIKE '%Nume pacient%')
    RETURNING id, cnp, LEFT(COALESCE(nume,''),80) as numenou, LEFT(COALESCE(prenume,''),40) as prenumenou
""")
extras = cur.fetchall()
if extras:
    print("\n=== Fix general (alte nume corupte) ===")
    for r in extras:
        print(f"  [{r['id']}] {r['cnp']} -> {r['numenou']} | {r['prenumenou']}")
conn.commit()

# Curata si cazurile > 80 chars cu regex simplu
cur.execute("""SELECT id, cnp, nume FROM pacienti WHERE LENGTH(COALESCE(nume,'')) > 60""")
lungi = cur.fetchall()
if lungi:
    print("\n=== Nume prea lungi (curatare simpla) ===")
    for r in lungi:
        print(f"  [{r['id']}] {r['cnp']}: {r['nume'][:80]}")

print("\n=== Pacienti dupa fix ===")
cur.execute("SELECT id, cnp, LEFT(COALESCE(nume,''),80) as nume, LEFT(COALESCE(prenume,''),40) as prenume FROM pacienti ORDER BY id")
for r in cur.fetchall():
    print(f"  [{r['id']}] {r['cnp']} | {r['nume']} | {r['prenume']}")

conn.close()
print("\nOK - fix aplicat.")
