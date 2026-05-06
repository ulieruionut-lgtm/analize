import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)

conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Gaseste pacientul Laza si buletinele
cur.execute("""
    SELECT p.id as pacient_id, p.nume, b.id as buletin_id, b.data_buletin
    FROM pacienti p
    JOIN buletine b ON b.pacient_id = p.id
    WHERE p.nume ILIKE '%Laza%'
    ORDER BY b.data_buletin
""")
buletine = cur.fetchall()
print("Buletine Laza:")
for b in buletine:
    print(f"  B{b['buletin_id']} - {b['data_buletin']} - {b['nume']}")

# Cauta buletinul din 05.12
buletin_id = None
for b in buletine:
    d = str(b['data_buletin'])
    if '-12-05' in d:
        buletin_id = b['buletin_id']
        print(f"\nGasit buletin: B{buletin_id} ({b['data_buletin']})")
        break

if not buletin_id:
    print("\nBuletinul din 05.12 nu a fost gasit.")
    conn.close()
    sys.exit(0)

# Afiseaza rezultatele din acel buletin
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.unitate,
           r.analiza_standard_id,
           a.denumire_standard, a.cod_standard
    FROM rezultate_analize r
    LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE r.buletin_id = %s
    ORDER BY r.id
""", (buletin_id,))
rezultate = cur.fetchall()
print(f"\nRezultate in B{buletin_id} ({len(rezultate)} total):")
for r in rezultate:
    mapped = r['denumire_standard'] or '--- FARA MAPARE ---'
    unitate = r['unitate'] or ''
    print(f"  RID={r['id']:4d} | raw='{r['denumire_raw']}' -> {mapped} | val={r['valoare']} {unitate}")

# Identifica analize care au mapare dar raw-ul e diferit de standard (candidati pentru alias)
print("\n--- Candidati pentru alias nou ---")
aliasuri_de_adaugat = []
for r in rezultate:
    raw = (r['denumire_raw'] or '').strip()
    std = r['denumire_standard'] or ''
    std_id = r['analiza_standard_id']
    if std_id and raw and raw.lower() != std.lower():
        aliasuri_de_adaugat.append({
            'denumire_raw': raw,
            'analiza_standard_id': std_id,
            'denumire_standard': std
        })
        print(f"  raw='{raw}' -> std='{std}' (ID={std_id})")

if not aliasuri_de_adaugat:
    print("  Niciun alias nou de adaugat (raw-urile coincid cu standardele).")
    conn.close()
    sys.exit(0)

# Adauga aliasuri noi (daca nu exista deja)
print("\n--- Adaugare aliasuri ---")
for a in aliasuri_de_adaugat:
    cur.execute(
        "SELECT id FROM analiza_alias WHERE LOWER(alias) = LOWER(%s)",
        (a['denumire_raw'],)
    )
    existing = cur.fetchone()
    if existing:
        print(f"  EXISTA deja: '{a['denumire_raw']}'")
    else:
        cur.execute(
            "INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s, %s)",
            (a['denumire_raw'], a['analiza_standard_id'])
        )
        print(f"  ADAUGAT: '{a['denumire_raw']}' -> '{a['denumire_standard']}'")

conn.commit()
print("\nGata! Aliasurile au fost salvate in DB.")
conn.close()
