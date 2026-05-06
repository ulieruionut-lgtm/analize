import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Ultimele 5 buletine incarcate
cur.execute("""
    SELECT b.id, b.data_buletin, b.created_at, p.nume,
           COUNT(r.id) as nr_rezultate,
           COUNT(r.analiza_standard_id) as nr_mapate,
           COUNT(CASE WHEN r.analiza_standard_id IS NULL THEN 1 END) as nr_nemapate,
           COUNT(r.valoare_text) as nr_text
    FROM buletine b
    JOIN pacienti p ON p.id = b.pacient_id
    LEFT JOIN rezultate_analize r ON r.buletin_id = b.id
    GROUP BY b.id, b.data_buletin, b.created_at, p.nume
    ORDER BY b.created_at DESC
    LIMIT 6
""")
buletine = cur.fetchall()
print("=== Ultimele buletine incarcate ===")
for b in buletine:
    print(f"\n  B{b['id']} | {b['nume']} | data buletin: {b['data_buletin'].date() if b['data_buletin'] else 'N/A'} | incarcat: {b['created_at'].strftime('%d.%m.%Y %H:%M')}")
    print(f"     Total: {b['nr_rezultate']} | Mapate: {b['nr_mapate']} | Nemapate: {b['nr_nemapate']} | Cu valoare text: {b['nr_text']}")

# Compara ultimele 2 buletine cu aceeasi data sau acelasi pacient
if len(buletine) >= 2:
    b1 = buletine[0]
    b2 = buletine[1]
    print(f"\n\n=== COMPARATIE B{b2['id']} (vechi) vs B{b1['id']} (nou) ===")

    for bul_id, label in [(b2['id'], "VECHI (prima incarcare)"), (b1['id'], "NOU (a doua incarcare)")]:
        cur.execute("""
            SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate,
                   r.analiza_standard_id, a.denumire_standard
            FROM rezultate_analize r
            LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
            WHERE r.buletin_id = %s
            ORDER BY r.id
        """, (bul_id,))
        rez = cur.fetchall()
        print(f"\n--- B{bul_id} {label}: {len(rez)} rezultate ---")
        for r in rez:
            std = r['denumire_standard'] or '!!! NEMAPAT'
            val = r['valoare_text'] if r['valoare_text'] else str(r['valoare'])
            print(f"  {std:45s} | val={val} {r['unitate'] or ''}")
            if not r['analiza_standard_id']:
                print(f"    RAW: '{r['denumire_raw']}'")

conn.close()
