import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── 1. Sterge cele 4 gunoi ramase in Laza B31 ────────────────────────────────
print("1. Sterg gunoi ramas in Laza B31:")
gunoi_rids = [981, 982, 983, 984]
for rid in gunoi_rids:
    cur.execute("SELECT denumire_raw, valoare FROM rezultate_analize WHERE id=%s", (rid,))
    r = cur.fetchone()
    if r:
        cur.execute("DELETE FROM rezultate_analize WHERE id=%s", (rid,))
        print(f"   STERS RID={rid}: '{r['denumire_raw']}' = {r['valoare']}")

# ── 2. Adauga aliasuri pentru raw-urile mapate dar fara alias ────────────────
print("\n2. Adaug aliasuri pentru raw-uri fara alias (invatare retroactiva):")
cur.execute("""
    SELECT DISTINCT r.denumire_raw, a.id as std_id, a.denumire_standard
    FROM rezultate_analize r
    JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE r.denumire_raw IS NOT NULL
      AND LOWER(r.denumire_raw) != LOWER(a.denumire_standard)
      AND LENGTH(r.denumire_raw) > 3
      AND NOT EXISTS (
          SELECT 1 FROM analiza_alias aa WHERE LOWER(aa.alias) = LOWER(r.denumire_raw)
      )
    ORDER BY a.denumire_standard
""")
de_invatat = cur.fetchall()
print(f"   Gasit {len(de_invatat)} raw-uri noi de invatat:")
adaugate = 0
for r in de_invatat:
    # Skip gunoi evident
    raw = r['denumire_raw']
    if any(x in raw for x in ['Absenti Absenti', 'Pg.', 'eGFR: ', 'k =', 'crescute', 'Interpretare', 'TRIGLICERIDE 1']):
        print(f"   SKIP gunoi: '{raw}'")
        continue
    try:
        cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (raw, r['std_id']))
        if cur.rowcount > 0:
            print(f"   NOU: '{raw}' -> {r['denumire_standard']}")
            adaugate += 1
    except Exception as e:
        print(f"   ERR: '{raw}' -> {e}")
print(f"   Total adaugate: {adaugate}")

# ── 3. Statistici finale ─────────────────────────────────────────────────────
conn.commit()
print("\n=== STATISTICI FINALE ===")
cur.execute("SELECT COUNT(*) as n FROM analiza_standard")
print(f"Analize standard: {cur.fetchone()['n']}")
cur.execute("SELECT COUNT(*) as n FROM analiza_alias")
print(f"Aliasuri invatate total: {cur.fetchone()['n']}")
cur.execute("SELECT COUNT(*) as n FROM analiza_necunoscuta")
print(f"Analiza_necunoscuta: {cur.fetchone()['n']}")

print("\n=== REZULTATE NEMAPATE DUPA FIX ===")
cur.execute("""
    SELECT r.denumire_raw, r.valoare, r.valoare_text,
           p.nume AS pacient, b.data_buletin, r.buletin_id
    FROM rezultate_analize r
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE r.analiza_standard_id IS NULL
    ORDER BY p.nume, b.data_buletin
""")
nemapate = cur.fetchall()
if not nemapate:
    print("  ✓ ZERO analize nemapate in toate buletinele!")
else:
    print(f"  {len(nemapate)} ramase nemapate:")
    for r in nemapate:
        val = r['valoare_text'] or str(r['valoare'])
        print(f"  [{r['pacient']}] B{r['buletin_id']} ({r['data_buletin'].date() if r['data_buletin'] else '?'}) | '{r['denumire_raw']}' = {val}")

# ── 4. Sumar pe pacienti ─────────────────────────────────────────────────────
print("\n=== SUMAR BULETINE PE PACIENTI ===")
cur.execute("""
    SELECT p.nume, b.id as bid, b.data_buletin,
           COUNT(r.id) as total,
           COUNT(r.analiza_standard_id) as mapate
    FROM pacienti p
    JOIN buletine b ON b.pacient_id = p.id
    JOIN rezultate_analize r ON r.buletin_id = b.id
    GROUP BY p.nume, b.id, b.data_buletin
    ORDER BY p.nume, b.data_buletin
""")
for r in cur.fetchall():
    pct = int(r['mapate'] / r['total'] * 100) if r['total'] > 0 else 0
    status = "✓" if r['mapate'] == r['total'] else "!!"
    print(f"  {status} {r['nume']:25s} B{r['bid']} ({r['data_buletin'].date() if r['data_buletin'] else '?'}) | {r['mapate']}/{r['total']} ({pct}%)")

conn.close()
