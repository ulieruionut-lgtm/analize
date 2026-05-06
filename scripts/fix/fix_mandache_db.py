"""
Corecteaza datele Mandache: Trombocite trebuie 267.000, Leucocite 6.440.
Sterge asocierea gresita si insereaza corect daca e nevoie.
"""
import os, sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding="utf-8")
DB = os.environ.get("DATABASE_URL", "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway")
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Buletin Mandache 19.02.2026
cur.execute("""
    SELECT b.id FROM buletine b
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE LOWER(p.nume) LIKE '%mandache%' AND b.fisier_original LIKE '%19.02.2026%'
    ORDER BY b.id DESC LIMIT 1
""")
row = cur.fetchone()
if not row:
    print("Buletin Mandache 19.02.2026 negasit")
    conn.close()
    sys.exit(0)
buletin_id = row["id"]

# ID analize standard
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'PLT'")
plt_row = cur.fetchone()
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard IN ('WBC','LEU') OR denumire_standard ILIKE '%leucocite%' LIMIT 1")
leu_row = cur.fetchone()
plt_id = plt_row["id"] if plt_row else None
leu_id = leu_row["id"] if leu_row else None

# Gaseste rezultatul gresit: Trombocite cu valoare ~6440 (de fapt Leucocite)
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.analiza_standard_id
    FROM rezultate_analize r
    WHERE r.buletin_id = %s AND r.valoare BETWEEN 6400 AND 6500
""", (buletin_id,))
wrong_trombocite = cur.fetchone()
if wrong_trombocite and wrong_trombocite.get("analiza_standard_id") == plt_id:
    cur.execute("UPDATE rezultate_analize SET valoare = 267000, unitate = '/mm³', interval_min = 150000, interval_max = 370000 WHERE id = %s", (wrong_trombocite["id"],))
    print("Corectat: Trombocite 6440 -> 267000")
    # Adauga Leucocite 6440
    if leu_id:
        cur.execute("SELECT COALESCE(MAX(ordine),0)+1 FROM rezultate_analize WHERE buletin_id = %s", (buletin_id,))
        next_ord = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, unitate, interval_min, interval_max, ordine)
            VALUES (%s, %s, 'Leucocite', 6440, '/mm³', 4050, 11840, %s)
        """, (buletin_id, leu_id, next_ord))
        print("Adaugat: Leucocite 6.440 /mm³")
elif wrong_trombocite:
    # Valoarea 6440 e sub un alt parametru - poate Leucocite cu denumire gresita
    cur.execute("UPDATE rezultate_analize SET denumire_raw = 'Leucocite', analiza_standard_id = %s WHERE id = %s", (leu_id or 0, wrong_trombocite["id"]))
    print("Corectat denumire pentru valoare 6440 -> Leucocite")
else:
    print("Nu s-a gasit rezultat gresit (Trombocite=6440)")

# Sterge "F, 28 ani" / "M, X ani" (gunoi)
cur.execute("""
    DELETE FROM rezultate_analize
    WHERE buletin_id = %s AND (denumire_raw ILIKE 'F,%%' OR denumire_raw ILIKE 'M,%%')
""", (buletin_id,))
if cur.rowcount:
    print("Sters:", cur.rowcount, "intrari gunoi (F,/M,)")

conn.commit()
conn.close()
print("Gata.")
