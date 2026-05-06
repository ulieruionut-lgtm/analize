import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("=== TOTI PACIENTII ===")
cur.execute("SELECT id, nume, cnp FROM pacienti ORDER BY nume")
for p in cur.fetchall():
    cur.execute("SELECT COUNT(*) as n FROM buletine WHERE pacient_id=%s", (p['id'],))
    nb = cur.fetchone()['n']
    print(f"  ID={p['id']} {p['nume']} (cnp={p['cnp']}) - {nb} buletine")

print("\n=== TOATE BULETINELE (ID mari) ===")
cur.execute("""
    SELECT b.id, b.data_buletin, p.nume,
           COUNT(r.id) as total,
           COUNT(r.analiza_standard_id) as mapate
    FROM buletine b
    JOIN pacienti p ON p.id=b.pacient_id
    LEFT JOIN rezultate_analize r ON r.buletin_id=b.id
    GROUP BY b.id, b.data_buletin, p.nume
    ORDER BY b.id DESC LIMIT 20
""")
for r in cur.fetchall():
    pct = int(r['mapate']/r['total']*100) if r['total'] > 0 else 0
    status = "✓" if r['mapate'] == r['total'] else "!!"
    print(f"  {status} B{r['id']} {r['nume']:25s} ({r['data_buletin'].date() if r['data_buletin'] else '?'}) | {r['mapate']}/{r['total']} ({pct}%)")

conn.close()
