# -*- coding: utf-8 -*-
"""
Curata gunoi din DB si corecteaza valori parsate gresit.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import psycopg2, psycopg2.extras
DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ID-uri de sters - gunoi pur (fara valoare medicala)
# Benchea B39 + B51
ids_sterge_benchea = [
    1357, 1358, 1359, 1360, 1361, 1362, 1364,
    1391, 1394, 1396, 1400, 1401, 1402, 1404, 1405, 1406,
    1407, 1408, 1410, 1411, 1412,
    # B51 - duplicate ale aceleiasi probleme
    1840, 1841, 1842, 1843, 1844, 1845, 1847,
    1874, 1877, 1879, 1883, 1884, 1885, 1887, 1888, 1889,
    1890, 1891, 1894, 1895,
]

# Iancu B48 + B55 - gunoi OCR (valori parsate gresit)
# HOT -> HCT (corectam, nu stergem)
# Hemoglobina, Cu E -> corectam denumire
# Restul = gunoi
ids_sterge_iancu = [
    1699, 1702, 1703, 1704, 1705, 1706, 1707, 1709,
    1712, 1719, 1720, 1722, 1728, 1734, 1735,
    # B55
    1939, 1942, 1943, 1944, 1945, 1946, 1947, 1949,
    1952, 1959, 1960, 1962, 1968, 1974, 1975,
]

# Nitu B57
ids_sterge_nitu = [1987, 1991, 1992, 1997]

# Mandache B59
ids_sterge_mandache = [2026]

# Vladasel Elena B63 - gunoi si footer
ids_sterge_vladasel = [
    2173, 2174, 2175, 2176, 2177, 2178, 2179, 2180, 2181,
    2183, 2193, 2204, 2212, 2217,
]

# Corectari de denumire (HOT -> HCT = Hematocrit)
# Gasim analiza_standard_id pentru HCT
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'HCT'")
r = cur.fetchone()
hct_id = r['id'] if r else None

cur.execute("SELECT id FROM analiza_standard WHERE cod_standard = 'HGB'")
r = cur.fetchone()
hgb_id = r['id'] if r else None

if hct_id:
    # HOT, -> HCT (Hematocrit 39.5%)
    cur.execute("""
        UPDATE rezultate_analize SET denumire_raw = 'HCT (Hematocrit)', analiza_standard_id = %s
        WHERE id IN (1730, 1970)
    """, (hct_id,))
    print(f"HCT fix (HOT,): {cur.rowcount} randuri")

if hgb_id:
    # Hemoglobina, Cu E -> Hemoglobina
    cur.execute("""
        UPDATE rezultate_analize SET denumire_raw = 'Hemoglobina', analiza_standard_id = %s
        WHERE id IN (1729, 1969)
    """, (hgb_id,))
    print(f"HGB fix (Hemoglobina, Cu E): {cur.rowcount} randuri")

# Nitu: Neutrofile 2.260/mm3 - valoare 1.0 cu denumire gresita
# id=1992: val=56.78 | Neutrofile 2.260/mm³ -> asta e gunoi (56.78 nu e neutrofile %)
# id=1991: val=1.0 | M, -> gunoi
# id=1997: val=4.0 | Răspuns rapid... -> gunoi
# id=1987: val=None | Hemoleucogramă -> header, sterge

# Sterge tot gunoiul
toate_ids = (ids_sterge_benchea + ids_sterge_iancu + ids_sterge_nitu +
             ids_sterge_mandache + ids_sterge_vladasel)

cur.execute("DELETE FROM rezultate_analize WHERE id = ANY(%s)", (toate_ids,))
print(f"Sterse {cur.rowcount} randuri de gunoi din DB")

conn.commit()

# Verifica rezultat
cur.execute("""
    SELECT b.id, p.nume, COUNT(ra.id) as total,
           SUM(CASE WHEN ra.analiza_standard_id IS NULL THEN 1 ELSE 0 END) as nec
    FROM buletine b
    JOIN pacienti p ON b.pacient_id = p.id
    LEFT JOIN rezultate_analize ra ON ra.buletin_id = b.id
    GROUP BY b.id, p.nume
    ORDER BY b.id
""")
print("\n=== Buletine dupa curatare ===")
for r in cur.fetchall():
    print(f"  B{r['id']} {r['nume']} | {r['total']} analize, {r['nec']} necunoscute")

conn.close()
print("\nOK - gunoi sters.")
