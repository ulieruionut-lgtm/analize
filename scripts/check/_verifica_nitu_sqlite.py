# -*- coding: utf-8 -*-
import sys, io, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_path = r"D:\Ionut analize\analize.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Gasim pacientul Nitu
cur.execute("SELECT id, cnp, nume, prenume FROM pacienti WHERE cnp = '5240222080031' OR LOWER(COALESCE(nume,'')) LIKE '%nitu%'")
pacienti = cur.fetchall()
print("Pacienti gasiti:")
for p in pacienti:
    print(f"  id={p['id']} cnp={p['cnp']} {p['nume']} {p['prenume']}")

if not pacienti:
    print("Pacientul nu exista in DB!")
    conn.close()
    sys.exit(0)

pac_id = pacienti[0]['id']

# Buletine
cur.execute("SELECT id, data_recoltare, fisier_sursa FROM buletine WHERE pacient_id = ? ORDER BY data_recoltare DESC", (pac_id,))
buletine = cur.fetchall()
print(f"\nBuletine ({len(buletine)}):")
for b in buletine:
    print(f"  buletin id={b['id']} data={b['data_recoltare']} fisier={b['fisier_sursa']}")

# Rezultate pentru fiecare buletin
for b in buletine:
    cur.execute("""
        SELECT ra.id, ra.denumire_raw, ra.valoare, ra.unitate, 
               COALESCE(ans.cod_standard, '?') as cod, COALESCE(ans.denumire, '?') as denumire_std
        FROM rezultate_analize ra
        LEFT JOIN analiza_standard ans ON ans.id = ra.analiza_standard_id
        WHERE ra.buletin_id = ?
        ORDER BY ra.id
    """, (b['id'],))
    rezultate = cur.fetchall()
    print(f"\n  Buletin {b['id']} ({b['data_recoltare']}) - {len(rezultate)} rezultate:")
    for r in rezultate:
        mapped = f"[{r['cod']}]" if r['cod'] != '?' else "[NEMAPAT]"
        print(f"    {mapped} {r['denumire_raw']} = {r['valoare']} {r['unitate']}")

conn.close()
