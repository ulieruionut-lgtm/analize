import psycopg2, psycopg2.extras
DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Alias-uri OCR pentru termeni din PDF Iancu (scanat prost)
# Format: (alias_raw, cod_standard)
ALIASURI = [
    ("HOT,", "HCT"),
    ("HOT", "HCT"),
    ("Hemoglobina, Cu E", "HB"),
    ("Hemoglobina,", "HB"),
    # Urobilinogen cu prefix OCR
    ("_UROBILINOGEN", "UBIL"),
    ("_UROBILINOGEN,", "UBIL"),
    # Nitriti cu ghilimele OCR
    ('NITRITI,', "NIT"),
    # Culoare urina cu asterisk
    ("Culoare*", "CULOARE_URINA"),
    ("Claritate*", "CLARITATE_URINA"),
    ("Aspect*", "ASPECT_URINA"),
]

print("=== Aliasuri disponibile pentru aceste coduri ===")
coduri = list({a[1] for a in ALIASURI})
cur.execute("SELECT id, cod_standard, denumire_standard FROM analiza_standard WHERE cod_standard = ANY(%s)", (coduri,))
std_map = {}
for r in cur.fetchall():
    std_map[r['cod_standard']] = r['id']
    print(f"  {r['cod_standard']} -> id={r['id']} ({r['denumire_standard']})")

print("\n=== Adaugare aliasuri ===")
adaugate = 0
for alias, cod in ALIASURI:
    sid = std_map.get(cod)
    if not sid:
        print(f"  SKIP: {cod} nu exista in analiza_standard")
        continue
    cur.execute(
        "INSERT INTO analiza_alias (analiza_standard_id, alias) VALUES (%s, %s) ON CONFLICT (alias) DO NOTHING",
        (sid, alias)
    )
    if cur.rowcount:
        print(f"  + '{alias}' -> {cod} (id={sid})")
        adaugate += 1
    else:
        print(f"  = '{alias}' deja exista")

conn.commit()
print(f"\n{adaugate} aliasuri noi adaugate. Sistemul va recunoaste aceste denumiri la upload-uri viitoare.")
conn.close()
