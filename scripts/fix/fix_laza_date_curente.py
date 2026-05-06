"""Corecteaza datele gresite din buletinele Laza (45, 46) fara a sterge nimic."""
import os
import sys
import psycopg2
import psycopg2.extras

sys.stdout.reconfigure(encoding="utf-8")

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway",
)

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # --- Buletin 45: RDW 124.0 -> 12.4 (punct zecimal pierdut OCR) ---
    cur.execute("""
        UPDATE rezultate_analize r
        SET valoare = 12.4
        FROM buletine b, pacienti p
        WHERE r.buletin_id = b.id AND b.pacient_id = p.id
          AND p.nume ILIKE '%Laza%' AND b.id = 45
          AND (r.denumire_raw ILIKE '%RDW%' OR r.denumire_raw ILIKE '%distributie%eritrocit%')
          AND r.valoare = 124.0
        RETURNING r.id, r.denumire_raw, r.valoare
    """)
    rdw_rows = cur.fetchall()
    if rdw_rows:
        print("Buletin 45 - RDW corectat 124.0 -> 12.4:")
        for r in rdw_rows:
            print(f"  id={r['id']} {r['denumire_raw'][:50]} -> 12.4")
    else:
        print("Buletin 45 - RDW: nu s-a gasit 124.0 de corectat (poate e deja corect)")

    # --- Buletin 46: Mucus valoare_text "Rar" -> "Absent" (swap gresit la parsare) ---
    cur.execute("""
        UPDATE rezultate_analize r
        SET valoare_text = 'Absent'
        FROM buletine b, pacienti p
        WHERE r.buletin_id = b.id AND b.pacient_id = p.id
          AND p.nume ILIKE '%Laza%' AND b.id = 46
          AND (r.denumire_raw ILIKE '%Mucus%' OR r.denumire_raw = 'Mucus Absent')
          AND r.valoare_text = 'Rar'
        RETURNING r.id, r.denumire_raw, r.valoare_text
    """)
    muc_rows = cur.fetchall()
    if muc_rows:
        print("\nBuletin 46 - Mucus corectat Rar -> Absent:")
        for r in muc_rows:
            print(f"  id={r['id']} {r['denumire_raw']} -> Absent")
    else:
        print("\nBuletin 46 - Mucus: nu s-a gasit Rar de corectat")

    # --- Buletin 46: Bilirubina Negativ - asigura mapare corecta ---
    # Daca avem raw "Bilirubina Negativ", curata la "Bilirubina" si mapam la Bilirubina urina
    cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'BILIRUBINA_URINA'")
    bil_urina = cur.fetchone()
    if bil_urina:
        cur.execute("""
            UPDATE rezultate_analize r
            SET denumire_raw = 'Bilirubina', analiza_standard_id = %s
            FROM buletine b, pacienti p
            WHERE r.buletin_id = b.id AND b.pacient_id = p.id
              AND p.nume ILIKE '%%Laza%%' AND b.id = 46
              AND r.denumire_raw = 'Bilirubina Negativ'
            RETURNING r.id
        """, (bil_urina['id'],))
        bil_rows = cur.fetchall()
        if bil_rows:
            print("\nBuletin 46 - Bilirubina: denumire_raw curatata si mapata la Bilirubina urina")
    else:
        # Adauga alias daca lipseste
        cur.execute("SELECT id FROM analiza_standard WHERE cod_standard IN ('BILIRUBIN_TOT','BILIRUBINA_URINA') LIMIT 1")
        any_bil = cur.fetchone()
        if any_bil:
            print("\nBuletin 46 - Bilirubina: verificare mapare (BILIRUBINA_URINA poate lipsi)")

    # --- Buletin 46: Mucus Absent - mapare la Mucus urina ---
    cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'MUCUS_URINA'")
    muc_std = cur.fetchone()
    if muc_std:
        cur.execute("""
            UPDATE rezultate_analize r
            SET denumire_raw = 'Mucus', analiza_standard_id = %s
            FROM buletine b, pacienti p
            WHERE r.buletin_id = b.id AND b.pacient_id = p.id
              AND p.nume ILIKE '%%Laza%%' AND b.id = 46
              AND r.denumire_raw = 'Mucus Absent'
            RETURNING r.id
        """, (muc_std['id'],))
        if cur.fetchall():
            print("\nBuletin 46 - Mucus: mapat la Mucus urina")
        # Adauga alias pentru viitor
        cur.execute(
            "INSERT INTO analiza_alias (analiza_standard_id, alias) VALUES (%s, 'Mucus Absent') ON CONFLICT (alias) DO NOTHING",
            (muc_std['id'],),
        )

    # --- Buletin 42: MPV 99.0 -> 9.9 (OCR punct zecimal pierdut) ---
    cur.execute("""
        UPDATE rezultate_analize r
        SET valoare = 9.9
        FROM buletine b, pacienti p
        WHERE r.buletin_id = b.id AND b.pacient_id = p.id
          AND p.nume ILIKE '%%Laza%%' AND b.id = 42
          AND (r.denumire_raw ILIKE '%%MPV%%' OR r.denumire_raw ILIKE '%%plachetar%%')
          AND r.valoare = 99.0
        RETURNING r.id, r.denumire_raw
    """)
    mpv_rows = cur.fetchall()
    if mpv_rows:
        print("\nBuletin 42 - MPV corectat 99.0 -> 9.9:")

    conn.commit()
    print("\nCorectii aplicate. Verifica in aplicatie.")
    conn.close()

if __name__ == "__main__":
    main()
