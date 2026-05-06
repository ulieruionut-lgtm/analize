"""Verifica pacientul Vladasel in baza de date."""
import os, sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding="utf-8")
DB = os.environ.get("DATABASE_URL", "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway")
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT p.id, p.cnp, p.nume, p.prenume FROM pacienti p
    WHERE LOWER(p.nume) LIKE '%vladasel%' OR LOWER(p.prenume) LIKE '%vladasel%'
       OR LOWER(p.nume || ' ' || COALESCE(p.prenume,'')) LIKE '%vladasel%'
""")
rows = cur.fetchall()
print("Pacienti Vladasel:", rows)

for p in rows:
    cur.execute("SELECT id, data_buletin, fisier_original FROM buletine WHERE pacient_id = %s", (p["id"],))
    buletine = cur.fetchall()
    print(f"\nBuletine pentru {p['nume']}:", buletine)
    for b in buletine:
        cur.execute("""
            SELECT r.denumire_raw, r.valoare, r.valoare_text, r.unitate, a.denumire_standard, r.categorie
            FROM rezultate_analize r LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
            WHERE r.buletin_id = %s ORDER BY COALESCE(r.ordine,999), r.id
        """, (b["id"],))
        rez = cur.fetchall()
        print(f"  Buletin {b['id']}: {len(rez)} rezultate")
        for z in rez:
            print("   ", z.get("denumire_raw"), "->", z.get("valoare") or z.get("valoare_text"), z.get("unitate"), "| std:", z.get("denumire_standard"))

conn.close()
