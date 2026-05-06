"""Corecteaza valorile gresite in buletinele Laza (calciu, fier seric)"""
import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding="utf-8")
DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur2 = conn.cursor()

# Verifica starea actuala
cur.execute("""
    SELECT r.id, r.buletin_id, r.denumire_raw, r.valoare, r.unitate, a.denumire_standard
    FROM rezultate_analize r
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE LOWER(p.nume) LIKE '%laza%'
      AND (LOWER(r.denumire_raw) LIKE '%calciu seric%'
        OR LOWER(r.denumire_raw) LIKE '%fier seric%')
    ORDER BY r.buletin_id, r.id
""")
rows = cur.fetchall()
print("=== Calciu + Fier inainte de corectie ===")
for r in rows:
    print(f"  id={r['id']} bul={r['buletin_id']} raw={r['denumire_raw']!r} val={r['valoare']} {r['unitate']}")

# Corecteaza CALCIU SERIC cu valoare 0.66 -> 10.66 (din buletin 42, parsare gresita)
cur2.execute("""
    UPDATE rezultate_analize
    SET valoare = 10.66
    WHERE id IN (
        SELECT r.id FROM rezultate_analize r
        JOIN buletine b ON b.id = r.buletin_id
        JOIN pacienti p ON p.id = b.pacient_id
        WHERE LOWER(p.nume) LIKE '%laza%'
          AND LOWER(r.denumire_raw) LIKE '%calciu seric%'
          AND r.valoare = 0.66
    )
""")
print(f"Corectate {cur2.rowcount} intrari CALCIU SERIC (0.66 -> 10.66)")

# Corecteaza FIER SERIC cu valoare 97.52 -> 197.52
cur2.execute("""
    UPDATE rezultate_analize
    SET valoare = 197.52
    WHERE id IN (
        SELECT r.id FROM rezultate_analize r
        JOIN buletine b ON b.id = r.buletin_id
        JOIN pacienti p ON p.id = b.pacient_id
        WHERE LOWER(p.nume) LIKE '%laza%'
          AND LOWER(r.denumire_raw) LIKE '%fier seric%'
          AND r.valoare = 97.52
          AND r.buletin_id = 42
    )
""")
print(f"Corectate {cur2.rowcount} intrari FIER SERIC (97.52 -> 197.52)")

conn.commit()

# Verifica dupa
cur.execute("""
    SELECT r.id, r.buletin_id, r.denumire_raw, r.valoare, r.unitate
    FROM rezultate_analize r
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE LOWER(p.nume) LIKE '%laza%'
      AND (LOWER(r.denumire_raw) LIKE '%calciu seric%'
        OR LOWER(r.denumire_raw) LIKE '%fier seric%')
    ORDER BY r.buletin_id, r.id
""")
rows = cur.fetchall()
print("\n=== Calciu + Fier dupa corectie ===")
for r in rows:
    print(f"  id={r['id']} bul={r['buletin_id']} raw={r['denumire_raw']!r} val={r['valoare']} {r['unitate']}")

conn.close()
print("\nGata!")
