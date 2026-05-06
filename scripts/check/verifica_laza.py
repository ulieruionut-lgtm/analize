import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding="utf-8")
DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("SELECT id, cnp, nume, prenume FROM pacienti WHERE LOWER(nume) LIKE '%laza%'")
pacienti = cur.fetchall()
print("=== PACIENTI LAZA ===")
for p in pacienti:
    print(f"  id={p['id']} cnp={p['cnp']} nume='{p['nume']}' prenume='{p['prenume']}'")

    cur.execute("SELECT id, data_buletin, fisier_original FROM buletine WHERE pacient_id = %s ORDER BY data_buletin", (p['id'],))
    buletine = cur.fetchall()
    print(f"  -> {len(buletine)} buletine:")
    for b in buletine:
        print(f"     buletin_id={b['id']} data={b['data_buletin']} fisier='{b['fisier_original']}'")
        cur.execute("""
            SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text, r.unitate,
                   r.interval_min, r.interval_max, r.flag, r.ordine, r.categorie,
                   a.denumire_standard, a.cod_standard
            FROM rezultate_analize r
            LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
            WHERE r.buletin_id = %s
            ORDER BY COALESCE(r.ordine, 99999), r.id
        """, (b['id'],))
        rez = cur.fetchall()
        print(f"     {len(rez)} analize:")
        for rr in rez:
            std = rr['denumire_standard'] or '?NEMAPAT?'
            val = rr['valoare'] if rr['valoare'] is not None else rr['valoare_text']
            print(f"       [{rr['categorie'] or '-'}] {rr['denumire_raw']!r:45s} -> {std:35s} = {val} {rr['unitate'] or ''}")

conn.close()
