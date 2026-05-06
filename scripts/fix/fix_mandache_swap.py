"""Corecteaza swap Trombocite/Leucocite la Mandache - cand denumire Trombocite arata valoare Leucocite."""
import os, sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding="utf-8")
DB = os.environ.get("DATABASE_URL", "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway")
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT b.id FROM buletine b
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE LOWER(p.nume) LIKE %s AND b.fisier_original LIKE %s
    ORDER BY b.id DESC LIMIT 1
""", ("%mandache%", "%19.02.2026%"))
row = cur.fetchone()
if not row:
    print("Buletin negasit")
    conn.close()
    sys.exit(0)
buletin_id = row["id"]

# Cauta randul Trombocite (PLT) cu valoare_text/denumire care arata Leucocite (swap)
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text
    FROM rezultate_analize r
    JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE r.buletin_id = %s AND a.cod_standard = 'PLT'
    AND (r.valoare_text ILIKE %s OR r.denumire_raw ILIKE %s)
""", (buletin_id, "%leucocite%6.440%", "%6.440%"))
wrong = cur.fetchone()
if not wrong:
    cur.execute("""
        SELECT r.id, r.denumire_raw, r.valoare, r.valoare_text FROM rezultate_analize r
        JOIN analiza_standard a ON a.id = r.analiza_standard_id
        WHERE r.buletin_id = %s AND a.cod_standard = 'PLT'
    """, (buletin_id,))
    wrong = cur.fetchone()

if wrong:
    # Corecteaza: Trombocite = 267000
    cur.execute("""
        UPDATE rezultate_analize
        SET valoare = 267000, valoare_text = NULL, unitate = '/mm³',
            interval_min = 150000, interval_max = 370000, denumire_raw = 'Trombocite'
        WHERE id = %s
    """, (wrong["id"],))
    print("Corectat Trombocite -> 267.000 /mm³")
    # Adauga Leucocite
    cur.execute("SELECT id FROM analiza_standard WHERE cod_standard IN ('WBC','LEU') OR denumire_standard ILIKE %s LIMIT 1", ("%leucocite%",))
    leu = cur.fetchone()
    if leu:
        cur.execute("SELECT COALESCE(MAX(ordine),0)+1 as n FROM rezultate_analize WHERE buletin_id = %s", (buletin_id,))
        ord = cur.fetchone()["n"]
        cur.execute("""
            INSERT INTO rezultate_analize (buletin_id, analiza_standard_id, denumire_raw, valoare, unitate, interval_min, interval_max, ordine)
            VALUES (%s, %s, 'Leucocite', 6440, '/mm³', 4050, 11840, %s)
        """, (buletin_id, leu["id"], ord))
        print("Adaugat Leucocite 6.440 /mm³")

conn.commit()
conn.close()
print("Gata.")
