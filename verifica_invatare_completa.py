import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── 1. Statistici generale ────────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) as n FROM analiza_standard")
print(f"Analize standard: {cur.fetchone()['n']}")
cur.execute("SELECT COUNT(*) as n FROM analiza_alias")
print(f"Aliasuri invatate: {cur.fetchone()['n']}")
cur.execute("SELECT COUNT(*) as n FROM analiza_necunoscuta")
print(f"Analize nerecunoscute (necunoscuta): {cur.fetchone()['n']}")

# ── 2. Rezultate NEMAPATE din toate buletinele ───────────────────────────────
print("\n=== REZULTATE NEMAPATE (analiza_standard_id IS NULL) ===")
cur.execute("""
    SELECT r.denumire_raw, r.valoare, r.valoare_text, r.unitate,
           p.nume AS pacient, b.data_buletin, r.buletin_id, r.id as rid
    FROM rezultate_analize r
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE r.analiza_standard_id IS NULL
    ORDER BY p.nume, b.data_buletin, r.id
""")
nemapate = cur.fetchall()
if not nemapate:
    print("  ✓ Nicio analiza nemapata!")
else:
    print(f"  {len(nemapate)} nemapate:")
    for r in nemapate:
        val = r['valoare_text'] or str(r['valoare'])
        print(f"  [{r['pacient']}] B{r['buletin_id']} | RID={r['rid']} | '{r['denumire_raw']}' = {val} {r['unitate'] or ''}")

# ── 3. Intrari in analiza_necunoscuta ────────────────────────────────────────
print("\n=== ANALIZA_NECUNOSCUTA (raw-uri nerecunoscute de normalizer) ===")
cur.execute("""
    SELECT an.denumire_raw, an.frecventa, an.prima_data_vazuta
    FROM analiza_necunoscuta an
    ORDER BY an.frecventa DESC, an.prima_data_vazuta DESC
    LIMIT 30
""")
nec = cur.fetchall()
if not nec:
    print("  ✓ Nicio intrare necunoscuta!")
else:
    print(f"  {len(nec)} (top 30):")
    for r in nec:
        print(f"  frecv={r['frecventa']} | '{r['denumire_raw']}' (prima: {r['prima_data_vazuta']})")

# ── 4. Aliasuri recente (ultimele 50 adaugate) ───────────────────────────────
print("\n=== ALIASURI RECENTE (ultimele 50) ===")
cur.execute("""
    SELECT aa.alias, a.denumire_standard, aa.id
    FROM analiza_alias aa
    JOIN analiza_standard a ON a.id = aa.analiza_standard_id
    ORDER BY aa.id DESC LIMIT 50
""")
for r in cur.fetchall():
    print(f"  ID={r['id']} '{r['alias']}' -> {r['denumire_standard']}")

# ── 5. Verifica daca raw-urile nemapate pot fi invatate ─────────────────────
print("\n=== POTENTIALE ALIASURI DE ADAUGAT ===")
cur.execute("""
    SELECT DISTINCT r.denumire_raw, a.denumire_standard, a.id as std_id
    FROM rezultate_analize r
    JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE r.denumire_raw IS NOT NULL
      AND LOWER(r.denumire_raw) != LOWER(a.denumire_standard)
      AND NOT EXISTS (
          SELECT 1 FROM analiza_alias aa WHERE LOWER(aa.alias) = LOWER(r.denumire_raw)
      )
    ORDER BY a.denumire_standard
    LIMIT 40
""")
posibile = cur.fetchall()
if not posibile:
    print("  ✓ Toate raw-urile mapate au deja alias!")
else:
    print(f"  {len(posibile)} raw-uri mapate dar fara alias:")
    for r in posibile:
        print(f"  '{r['denumire_raw']}' -> {r['denumire_standard']} (std_id={r['std_id']})")

conn.close()
