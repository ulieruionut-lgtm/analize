# encoding: utf-8
import psycopg2, psycopg2.extras, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1. Verifica ca aliasurile sunt salvate in DB
print("=== Aliasuri pentru textele OCR garbled ===")
TEXTE = ['i a ( )', 'a lit nr.', 'IRT aa cn aia aaa a ES A E NENEA a',
         'IRT aa cn aia aaa', 'i a()', 'a lit nr']
cur.execute("""
    SELECT aa.alias, aa.analiza_standard_id, ast.cod_standard
    FROM analiza_alias aa
    JOIN analiza_standard ast ON ast.id = aa.analiza_standard_id
    ORDER BY aa.id DESC LIMIT 30
""")
all_recent = cur.fetchall()
for row in all_recent:
    print(f"  '{row['alias']}' -> {row['cod_standard']}")

# 2. Verifica ultimele buletine uploadate
print("\n=== Ultimele buletine Laza ===")
cur.execute("""
    SELECT b.id, b.data_buletin, b.created_at,
           COUNT(r.id) as total,
           SUM(CASE WHEN r.analiza_standard_id IS NULL THEN 1 ELSE 0 END) as nerecunoscute
    FROM buletine b
    JOIN pacienti p ON p.id = b.pacient_id
    LEFT JOIN rezultate_analize r ON r.buletin_id = b.id
    WHERE p.cnp = '2780416131279'
    GROUP BY b.id, b.data_buletin, b.created_at
    ORDER BY b.id DESC
""")
for row in cur.fetchall():
    print(f"  B{row['id']} | {str(row['data_buletin'])[:10]} | creat={str(row['created_at'])[:19]} | total={row['total']} | gunoi={row['nerecunoscute']}")

# 3. Arata exact ce e nerecunoscut in ultimele buletine
print("\n=== Analize nerecunoscute in ultimele 3 buletine Laza ===")
cur.execute("""
    SELECT b.id as bid, r.id as rid, r.denumire_raw, r.valoare, r.unitate
    FROM rezultate_analize r
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE p.cnp = '2780416131279'
      AND r.analiza_standard_id IS NULL
      AND b.id IN (SELECT id FROM buletine WHERE pacient_id = (SELECT id FROM pacienti WHERE cnp='2780416131279') ORDER BY id DESC LIMIT 3)
    ORDER BY b.id DESC, r.id
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  B{row['bid']} rid={row['rid']} | [{row['denumire_raw']}] = {row['valoare']} {row['unitate'] or ''}")
else:
    print("  Niciuna! Totul e recunoscut.")

# 4. Verifica cum face matching normalizer-ul pentru aceste texte
print("\n=== Test matching pentru textele garbled ===")
import sys, os
os.chdir(r"D:\Ionut analize")
sys.path.insert(0, r"D:\Ionut analize")

# Seteaza DATABASE_URL pentru normalizer
os.environ["DATABASE_URL"] = DB

try:
    from backend.normalizer import _cauta_in_cache, invalideaza_cache
    invalideaza_cache()  # forteaza reincarcarea cache-ului
    
    texte_test = [
        "i a ( )",
        "a lit nr.",
        "IRT aa cn aia aaa a ES A E NENEA a",
        "14.2",
        "i ne soia ta a SE co",
    ]
    for text in texte_test:
        result = _cauta_in_cache(text)
        print(f"  '{text}' -> std_id={result}")
except Exception as e:
    print(f"  EROARE la test normalizer: {e}")

conn.close()
