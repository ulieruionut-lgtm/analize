"""
Corecteaza datele Nitu in DB: sterge intrari gresite, pastreaza corecte.
Dupa rulare, utilizatorul poate RE-INCARCA PDF-ul pentru a obtine parsarea completa.
"""
import os, sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding="utf-8")
DB = os.environ.get("DATABASE_URL", "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway")

conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Gaseste buletinul Nitu
cur.execute("""
    SELECT b.id FROM buletine b
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE LOWER(p.nume) LIKE '%nitu%'
    ORDER BY b.id DESC LIMIT 1
""")
row = cur.fetchone()
if not row:
    print("Nu s-a gasit buletinul Nitu 13.02.2026")
    conn.close()
    sys.exit(0)
buletin_id = row["id"]

# Sterge intrari evident gresite (gunoi OCR / interpretari)
cur.execute("""
    DELETE FROM rezultate_analize
    WHERE buletin_id = %s AND (
        denumire_raw ILIKE '%%M,%%' AND (valoare_text ILIKE '%%an%%' OR valoare::text ILIKE '%%1%%')
        OR denumire_raw ILIKE '%%Răspuns rapid%%'
        OR denumire_raw ILIKE '%%Raspuns rapid%%'
    )
    RETURNING id, denumire_raw
""", (buletin_id,))
deleted = cur.fetchall()
for d in deleted:
    print("Sters:", d["denumire_raw"][:60])

# Sterge asociere gresita Hemoleucograma -> Hematii (denumire e antet)
cur.execute("""
    DELETE FROM rezultate_analize
    WHERE buletin_id = %s AND denumire_raw ILIKE 'Hemoleucogramă' AND analiza_standard_id IS NULL
    RETURNING id
""", (buletin_id,))
if cur.rowcount:
    print("Sters: Hemoleucogramă (antet gresit)")

# Sterge asociere gresita Trombocite -> valoare Leucocite
cur.execute("""
    SELECT id, denumire_raw, valoare FROM rezultate_analize
    WHERE buletin_id = %s AND denumire_raw ILIKE '%%Trombocite%%323%%' AND valoare = 3980
""", (buletin_id,))
wrong = cur.fetchall()
if wrong:
    cur.execute("DELETE FROM rezultate_analize WHERE id = %s", (wrong[0]["id"],))
    print("Sters: Trombocite cu valoare gresita (3980)")

conn.commit()
cur.execute("SELECT COUNT(*) as n FROM rezultate_analize WHERE buletin_id = %s", (buletin_id,))
n = cur.fetchone()["n"]
print(f"\nRezultate ramase in buletin: {n}")
print("Re-incarca PDF-ul Nitu pentru parsare completa (parserul a fost actualizat pentru Bioclinica).")
conn.close()
