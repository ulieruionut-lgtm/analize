import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)

conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Toate buletinele Laza
cur.execute("""
    SELECT b.id as buletin_id, b.data_buletin
    FROM pacienti p
    JOIN buletine b ON b.pacient_id = p.id
    WHERE p.nume ILIKE '%Laza%'
    ORDER BY b.data_buletin
""")
buletine = cur.fetchall()
ids = [f"B{b['buletin_id']} ({b['data_buletin'].date()})" for b in buletine]
print(f"Buletine Laza: {ids}\n")

# Toate rezultatele din buletinele Laza
cur.execute("""
    SELECT r.id, r.denumire_raw, r.analiza_standard_id,
           a.denumire_standard, a.cod_standard
    FROM rezultate_analize r
    LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE p.nume ILIKE '%Laza%'
      AND r.analiza_standard_id IS NOT NULL
      AND r.denumire_raw IS NOT NULL
      AND r.denumire_raw != ''
    ORDER BY a.denumire_standard, r.denumire_raw
""")
toate = cur.fetchall()

# Grupeaza candidatii unici pentru alias
candidati = {}
for r in toate:
    raw = r['denumire_raw'].strip()
    std = r['denumire_standard']
    std_id = r['analiza_standard_id']
    if raw.lower() != std.lower():
        candidati[raw] = (std_id, std)

print(f"Total candidati unici pentru alias: {len(candidati)}")

# Verifica care nu exista deja in analiza_alias
print("\n--- Procesare aliasuri ---")
adaugate = 0
existente = 0
for raw, (std_id, std) in sorted(candidati.items()):
    cur.execute(
        "SELECT id FROM analiza_alias WHERE LOWER(alias) = LOWER(%s)",
        (raw,)
    )
    if cur.fetchone():
        existente += 1
    else:
        cur.execute(
            "INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s, %s)",
            (raw, std_id)
        )
        print(f"  NOU: '{raw}' -> '{std}'")
        adaugate += 1

conn.commit()
print(f"\nRezultat: {adaugate} aliasuri NOI adaugate, {existente} existau deja.")

# Verifica si analize fara mapare (raw fara analiza_standard_id)
cur.execute("""
    SELECT DISTINCT r.denumire_raw, COUNT(*) as aparitii
    FROM rezultate_analize r
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE p.nume ILIKE '%Laza%'
      AND r.analiza_standard_id IS NULL
      AND r.denumire_raw IS NOT NULL
      AND r.denumire_raw != ''
    GROUP BY r.denumire_raw
    ORDER BY aparitii DESC
""")
nemapate = cur.fetchall()
if nemapate:
    print(f"\n--- Analize inca nemapate ({len(nemapate)}) ---")
    for n in nemapate:
        print(f"  '{n['denumire_raw']}' (apare de {n['aparitii']} ori)")
else:
    print("\nToate analizele Laza sunt mapate corect!")

conn.close()
