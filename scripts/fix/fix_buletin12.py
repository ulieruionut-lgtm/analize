"""Curata buletinul 12 (Laza 05.12.2025): sterge gunoi OCR, adauga alias-uri lips."""
import psycopg2, os
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

print("=== Curatare buletin_id=12 ===\n")

# 1. Sterge randurile gunoi (OCR artifacts)
cur.execute("""
    DELETE FROM rezultate_analize
    WHERE buletin_id=12
      AND denumire_raw IN (
        ': s i',
        'E e',
        'eGFR =',
        'eGFR: 60 -',
        'i Ea a acte o oa a',
        'k =',
        'o A',
        'PD'
      )
""")
print(f"Sterse {cur.rowcount} randuri gunoi OCR")

# 2. Mapeaza analizele fara cod_standard
# Vitamina D
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='VIT_D'")
row = cur.fetchone()
vit_d_id = row[0] if row else None
if vit_d_id:
    cur.execute("""
        UPDATE rezultate_analize
        SET analiza_standard_id=%s
        WHERE buletin_id=12 AND denumire_raw ILIKE '%%VITAMINA D%%'
          AND analiza_standard_id IS NULL
    """, (vit_d_id,))
    print(f"Vitamina D mapat: {cur.rowcount} randuri")

    # Adauga alias pentru viitor
    cur.execute("""
        INSERT INTO analiza_alias (analiza_standard_id, alias)
        VALUES (%s, '25-O0H-VITAMINA D')
        ON CONFLICT DO NOTHING
    """, (vit_d_id,))
    cur.execute("""
        INSERT INTO analiza_alias (analiza_standard_id, alias)
        VALUES (%s, '25-OH-VITAMINA D')
        ON CONFLICT DO NOTHING
    """, (vit_d_id,))
    cur.execute("""
        INSERT INTO analiza_alias (analiza_standard_id, alias)
        VALUES (%s, '25-OH VITAMINA D')
        ON CONFLICT DO NOTHING
    """, (vit_d_id,))

# Limfocite (LYM%) - OCR a scris "limE?oeite" in loc de "limfocite"
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='LIMFOCITE_PCT'")
row2 = cur.fetchone()
lym_id = row2[0] if row2 else None
if lym_id:
    cur.execute("""
        UPDATE rezultate_analize
        SET analiza_standard_id=%s
        WHERE buletin_id=12 AND denumire_raw ILIKE '%%LYM%%'
          AND analiza_standard_id IS NULL
    """, (lym_id,))
    print(f"Limfocite PCT mapat: {cur.rowcount} randuri")

    # Adauga alias cu variante OCR
    for alias in [
        'Procentul de limE?oeite (LYM%)',
        'Procentul de limfocite (LYM%)',
        'Procent limfocite (LYM%)',
        'LYM%',
    ]:
        cur.execute("""
            INSERT INTO analiza_alias (analiza_standard_id, alias)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, (lym_id, alias))

conn.commit()
cur.close()
conn.close()
print("\n=== Curatare finalizata! ===")
