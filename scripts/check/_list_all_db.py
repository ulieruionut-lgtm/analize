# -*- coding: utf-8 -*-
import sys, io, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_path = r"D:\Ionut analize\analize.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Lista toti pacientii
cur.execute("SELECT id, cnp, nume, prenume FROM pacienti ORDER BY id DESC LIMIT 20")
pacienti = cur.fetchall()
print("Ultimii 20 pacienti in DB:")
for p in pacienti:
    print(f"  id={p['id']} cnp={p['cnp']} {p['nume']} {p['prenume']}")

# Count buletine si rezultate
cur.execute("SELECT COUNT(*) as cnt FROM buletine")
r = cur.fetchone()
print(f"\nTotal buletine: {r['cnt']}")
cur.execute("SELECT COUNT(*) as cnt FROM rezultate_analize")
r = cur.fetchone()
print(f"Total rezultate: {r['cnt']}")

# Ultimele buletine
cur.execute("""
    SELECT b.id, b.data_recoltare, b.fisier_sursa, p.nume, p.prenume, p.cnp,
           COUNT(ra.id) as nr_rezultate
    FROM buletine b
    JOIN pacienti p ON p.id = b.pacient_id
    LEFT JOIN rezultate_analize ra ON ra.buletin_id = b.id
    GROUP BY b.id
    ORDER BY b.id DESC LIMIT 10
""")
buletine = cur.fetchall()
print("\nUltimele 10 buletine:")
for b in buletine:
    print(f"  [{b['id']}] {b['nume']} {b['prenume']} ({b['cnp']}) data={b['data_recoltare']} nr_rez={b['nr_rezultate']} fisier={b['fisier_sursa']}")

conn.close()
