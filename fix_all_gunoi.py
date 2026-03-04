# -*- coding: utf-8 -*-
"""Curatare completa gunoi din toate buletinele + mapare eGFR + alias-uri lips."""
import psycopg2, os
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

print("=== Curatare completa + mapare analize ===\n")

# ─── 1. Mapeaza eGFR corect ─────────────────────────────────────────────────
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='EGFR'")
row = cur.fetchone()
if not row:
    cur.execute("""
        INSERT INTO analiza_standard (cod_standard, denumire_standard, unitate_implicita, interval_min, interval_max)
        VALUES ('EGFR','Rata de filtrare glomerulara estimata (eGFR)','ml/min/1.73m2',60,120)
        RETURNING id
    """)
    row = cur.fetchone()
egfr_id = row[0]

for alias in ['eGFR =','eGFR=','eGFR','EGFR','Rata de filtrare glomerulara',
              'Rata estimata a filtrarii glomerulare (eGFR)*',
              'Rata estimata a filtrarii glomerulare (eGFR)',
              'Valoare eGFR:','Valoare eGFR','eGFR (CKD-EPI)',
              'RFGe','GFR','- eGFR*']:
    cur.execute("INSERT INTO analiza_alias (analiza_standard_id,alias) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (egfr_id, alias))

cur.execute("""
    UPDATE rezultate_analize SET analiza_standard_id=%s
    WHERE denumire_raw ILIKE 'eGFR%%' AND denumire_raw NOT ILIKE 'eGFR:%%'
      AND analiza_standard_id IS NULL
""", (egfr_id,))
cur.execute("""
    UPDATE rezultate_analize SET analiza_standard_id=%s
    WHERE denumire_raw ILIKE '%%filtrarii glomerulare%%'
      AND analiza_standard_id IS NULL
""", (egfr_id,))
cur.execute("""
    UPDATE rezultate_analize SET analiza_standard_id=%s
    WHERE denumire_raw ILIKE 'Valoare eGFR%%'
      AND analiza_standard_id IS NULL
""", (egfr_id,))
print(f"eGFR mapat (id={egfr_id}), alias-uri adaugate")

# ─── 2. Sterge randurile gunoi administrative/OCR ────────────────────────────
# Pattern-uri clare de gunoi: text administrativ, cod cerere, act, formular etc.
cur.execute("""
    DELETE FROM rezultate_analize
    WHERE analiza_standard_id IS NULL AND (
        denumire_raw ILIKE '%%Cod Cerere%%'
        OR denumire_raw ILIKE '%%Cod Proba%%'
        OR denumire_raw ILIKE '%%Formular:%%'
        OR denumire_raw ILIKE '%%Act: BV%%'
        OR denumire_raw ILIKE '%%Cont: RO%%'
        OR denumire_raw ILIKE '%%Regulamentul nr%%'
        OR denumire_raw ILIKE '%%Pagina%% din%%'
        OR denumire_raw ILIKE '%%uz personal%%'
        OR denumire_raw ILIKE '%%executate de parteneri%%'
        OR denumire_raw ILIKE '%%CERTIFICAT%%'
        OR denumire_raw ILIKE '%%ghidului KDIGO%%'
        OR denumire_raw ILIKE '%%Data nasterii%%'
        OR denumire_raw ILIKE '%%Spectrofotome%%'
        OR denumire_raw ILIKE '%%CITOMETRIE%%'
        OR denumire_raw ILIKE '%%Raspuns rapid%%'
        OR denumire_raw ILIKE '%%amoxicillin%%'
        OR denumire_raw ILIKE '%%Cefuroxime%%'
        OR denumire_raw ILIKE '%%diabet zaharat%%'
    )
""")
print(f"Randuri administrative sterse: {cur.rowcount}")

# Intervale de referinta (note clasificare, nu analize reale)
cur.execute("""
    DELETE FROM rezultate_analize
    WHERE analiza_standard_id IS NULL AND (
        denumire_raw ILIKE 'Usor crescut%%'
        OR denumire_raw ILIKE 'Moderat crescut%%'
        OR denumire_raw ILIKE 'Crescut%%'
        OR denumire_raw ILIKE 'Foarte crescut%%'
        OR denumire_raw ILIKE 'Acceptabil:%%'
        OR denumire_raw ILIKE 'Borderline%%'
        OR denumire_raw ILIKE 'Normal:%%'
        OR denumire_raw ILIKE 'Optim:%%'
        OR denumire_raw ILIKE 'Diabet%%'
        OR denumire_raw ILIKE 'trimestrul%%'
        OR denumire_raw ILIKE 'trimester%%'
        OR denumire_raw ILIKE 'eGFR:%%'
        OR denumire_raw ILIKE '- eGFR:%%'
        OR denumire_raw ILIKE 'persoane%%'
        OR denumire_raw ILIKE 'G1 =%%'
        OR denumire_raw ILIKE 'G2%%'
        OR denumire_raw ~ '^\d{1,2}-\d{1,2} ani'
        OR denumire_raw ~ '^\d{2}-\d{2} ani'
        OR denumire_raw ILIKE 'crescute%%'
        OR denumire_raw ILIKE '20-40 ani%%'
        OR denumire_raw ILIKE 'peste 40 ani%%'
        OR denumire_raw ILIKE 'persoanelor%%'
    )
""")
print(f"Intervale de referinta sterse: {cur.rowcount}")

# Artefacte OCR scurte si fara sens
cur.execute("""
    DELETE FROM rezultate_analize
    WHERE analiza_standard_id IS NULL AND (
        length(trim(denumire_raw)) <= 5
        OR denumire_raw ~ '^[: |]'
        OR denumire_raw ILIKE 'E e'
        OR denumire_raw ILIKE 'i Ia'
        OR denumire_raw ILIKE 'i Cea a'
        OR denumire_raw ILIKE 'i Ea a%'
        OR denumire_raw ILIKE 'M, '
        OR denumire_raw ILIKE 'F, '
        OR denumire_raw ~ '^[A-Z],\s'
    )
""")
print(f"Artefacte OCR scurte sterse: {cur.rowcount}")

# Linii cu nume de pacient sau date personale (parsate gresit)
cur.execute("""
    DELETE FROM rezultate_analize
    WHERE analiza_standard_id IS NULL AND (
        denumire_raw ILIKE '%%Varsta:%%'
        OR denumire_raw ILIKE '%%Varsta%%'
        OR denumire_raw ILIKE '%%ani,%%'
        OR denumire_raw ~ 'Nume\s+\w+'
        OR denumire_raw ILIKE '%%luna%%'
        OR denumire_raw ILIKE '%%in 0%%.%%.20%%'
    )
""")
print(f"Date personale parsate gresit sterse: {cur.rowcount}")

# ─── 3. Mapeaza analize reale nemapate ──────────────────────────────────────
# ALT/GPT/TGP
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='ALT'")
alt_id = (cur.fetchone() or [None])[0]
if alt_id:
    cur.execute("""
        UPDATE rezultate_analize SET analiza_standard_id=%s
        WHERE denumire_raw ILIKE '%%ALANINAMINOTRANSFERAZA%%' AND analiza_standard_id IS NULL
    """, (alt_id,))
    print(f"ALT mapat: {cur.rowcount} randuri")

# AST/GOT
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='AST'")
ast_id = (cur.fetchone() or [None])[0]
if ast_id:
    cur.execute("""
        UPDATE rezultate_analize SET analiza_standard_id=%s
        WHERE denumire_raw ILIKE '%%ASPARTATAMINOTRANSFERAZA%%' AND analiza_standard_id IS NULL
    """, (ast_id,))
    print(f"AST mapat: {cur.rowcount} randuri")

# MPV cu OCR garbled ('siehetie' in loc de 'plachetar')
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='MPV'")
mpv_id = (cur.fetchone() or [None])[0]
if mpv_id:
    cur.execute("""
        UPDATE rezultate_analize SET analiza_standard_id=%s
        WHERE denumire_raw ILIKE '%%mediu%%' AND denumire_raw ILIKE '%%(MPV)%%'
          AND analiza_standard_id IS NULL
    """, (mpv_id,))
    print(f"MPV mapat: {cur.rowcount} randuri")
    cur.execute("INSERT INTO analiza_alias (analiza_standard_id,alias) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (mpv_id, 'Volumul mediu siehetie (MPV)'))

conn.commit()
conn.close()
print("\n=== Curatare finalizata! ===")
