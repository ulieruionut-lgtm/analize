# encoding: utf-8
import psycopg2, psycopg2.extras, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ─── 0. Verifica B15 ──────────────────────────────────────────────────────────
print("=== Verifica buletin B15 ===")
cur.execute("SELECT id, data_buletin FROM buletine WHERE id = 15")
b15 = cur.fetchone()
print(f"  B15 exista: {b15}")
cur.execute("SELECT COUNT(*) as nr FROM rezultate_analize WHERE buletin_id = 15")
cnt = cur.fetchone()
print(f"  Analize in B15: {cnt['nr']}")

# ─── 1. Sterge B24 (4 analize, majoritate gunoi, duplicat partial) ──────────
print("\n=== Sterg buletin B24 (majoritate gunoi) ===")
cur.execute("DELETE FROM rezultate_analize WHERE buletin_id = 24")
print(f"  Sterse {cur.rowcount} rezultate din B24")
cur.execute("DELETE FROM buletine WHERE id = 24")
print(f"  B24 sters: {cur.rowcount}")

# ─── 2. Curata gunoi din B23 ──────────────────────────────────────────────────
print("\n=== Sterg gunoi din B23 ===")
RID_GUNOI_B23 = [
    857,   # [IRT aa cn aia aaa a ES A E NENEA a] - garbage
    869,   # [RETEAUA PRIVATA DE SANATATE Data - ora recoltare...] - antet clinic
    870,   # [Coad:5hn a] - cod de bare partial
    874,   # [E Cod:5] - cod partial
    877,   # [14.2] = 14.3 - intervalul de referinta citit ca denumire (HGB-ul e deja adaugat manual)
]
for rid in RID_GUNOI_B23:
    cur.execute("DELETE FROM rezultate_analize WHERE id = %s", (rid,))
    if cur.rowcount:
        print(f"  Sters rid={rid}")
    else:
        print(f"  rid={rid} deja absent")

# ─── 3. Corecteaza RDW: 124.0 -> 12.4 (decimal pierdut) ─────────────────────
print("\n=== Corectez RDW 124.0 -> 12.4 ===")
cur.execute("UPDATE rezultate_analize SET valoare = 12.4 WHERE id = 861")
print(f"  Updated: {cur.rowcount}")

# ─── 4. Mapeaza rid=865 [i a ( )] = 43.3 -> Limfocite % ─────────────────────
# Valoarea 43.3 corespunde LYM% din buletin 15 (22.12.2025)
print("\n=== Mapeaza rid=865 [i a ( )] = 43.3 -> LIMFOCITE_PCT ===")
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'LIMFOCITE_PCT'")
lym_std = cur.fetchone()
if lym_std:
    cur.execute("""
        UPDATE rezultate_analize
        SET analiza_standard_id = %s, denumire_raw = 'Procentul de limfocite (LYM%%)'
        WHERE id = 865
    """, (lym_std['id'],))
    print(f"  Mapat la std_id={lym_std['id']}: {cur.rowcount} updated")

# ─── 5. Verifica rid=876 [a lit nr.] = 679.0 ─────────────────────────────────
# 679 ar putea fi VIT_B12. Verificam daca B23 are deja VIT_B12
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.analiza_standard_id
    FROM rezultate_analize r
    WHERE r.buletin_id = 23 AND r.analiza_standard_id = 60
""")
existing_b12 = cur.fetchone()
if existing_b12:
    print(f"\n=== B23 are deja VIT_B12: rid={existing_b12['id']} val={existing_b12['valoare']} ===")
    # Stergem rid=876 (duplicat sau garbage)
    cur.execute("DELETE FROM rezultate_analize WHERE id = 876")
    print(f"  Sters rid=876 (duplicat): {cur.rowcount}")
else:
    # rid=876 [a lit nr.] = 679 - mapam la VIT_B12
    cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'VIT_B12'")
    b12_std = cur.fetchone()
    if b12_std:
        print(f"\n=== Mapez rid=876 [a lit nr.] = 679 -> VIT_B12 ===")
        cur.execute("""
            UPDATE rezultate_analize
            SET analiza_standard_id = %s, denumire_raw = 'VITAMINA B12'
            WHERE id = 876
        """, (b12_std['id'],))
        print(f"  Mapat la VIT_B12: {cur.rowcount}")

# ─── 6. Arata starea finala B23 ──────────────────────────────────────────────
print("\n=== Stare finala B23 ===")
cur.execute("""
    SELECT r.id as rid, r.analiza_standard_id, ast.cod_standard, r.denumire_raw, r.valoare
    FROM rezultate_analize r
    LEFT JOIN analiza_standard ast ON ast.id = r.analiza_standard_id
    WHERE r.buletin_id = 23
    ORDER BY r.id
""")
total = 0
gunoi = 0
for row in cur.fetchall():
    total += 1
    if row['analiza_standard_id'] is None:
        gunoi += 1
        print(f"  [GUNOI] rid={row['rid']} | [{row['denumire_raw']}] = {row['valoare']}")
    else:
        print(f"  [ok] rid={row['rid']} | std={row['cod_standard']} | [{row['denumire_raw']}] = {row['valoare']}")
print(f"\n  Total: {total} | Recunoscute: {total-gunoi} | Gunoi: {gunoi}")

# ─── 7. Verifica alti pacienti cu gunoi ──────────────────────────────────────
print("\n=== Alti pacienti cu analize nerecunoscute ===")
cur.execute("""
    SELECT b.id as bid, p.nume, r.id as rid, r.denumire_raw, r.valoare
    FROM rezultate_analize r
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE r.analiza_standard_id IS NULL
    AND b.id NOT IN (20, 23)
    ORDER BY b.id, r.id
""")
for row in cur.fetchall():
    print(f"  B{row['bid']} ({row['nume']}) rid={row['rid']} | [{row['denumire_raw']}] = {row['valoare']}")

conn.commit()
print("\n=== COMMIT OK ===")
cur.close()
conn.close()
print("Gata!")
