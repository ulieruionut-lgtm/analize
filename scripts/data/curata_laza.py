"""
Curata buletinele Laza:
- Sterge buletin 43 (duplicat corupt al lui 42 - acelasi PDF cu OCR mai prost)
- Sterge buletin 44 daca exista (duplicat)
- Pastreaza 42 (03.12, 47 analize - cel mai bun)
- Pastreaza 45, 46, 31 (22.12 - date reale, diferite)
Sterge si analizele ?NEMAPAT? evidente (gunoi OCR) din toate buletinele Laza
"""
import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding="utf-8")
DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur2 = conn.cursor()

# 1. Sterge buletin 43 (duplicat corupt - acelasi PDF ca 42 dar OCR mai prost)
cur.execute("SELECT COUNT(*) as n FROM rezultate_analize WHERE buletin_id = 43")
print(f"Buletin 43: {cur.fetchone()['n']} analize - se sterge (duplicat corupt)")
cur2.execute("DELETE FROM rezultate_analize WHERE buletin_id = 43")
cur2.execute("DELETE FROM buletine WHERE id = 43")

# 2. Sterge buletin 44 daca exista
cur.execute("SELECT COUNT(*) as n FROM buletine WHERE id = 44")
if cur.fetchone()['n'] > 0:
    cur2.execute("DELETE FROM rezultate_analize WHERE buletin_id = 44")
    cur2.execute("DELETE FROM buletine WHERE id = 44")
    print("Buletin 44 sters")

# 3. Sterge gunoi OCR din buletinele ramase ale Lazei
# Pattern gunoi: denumire_raw cu litere unice/silabe scurte sau fraze lungi nemediale
cur.execute("""
    SELECT r.id, r.denumire_raw, r.buletin_id
    FROM rezultate_analize r
    JOIN buletine b ON b.id = r.buletin_id
    JOIN pacienti p ON p.id = b.pacient_id
    WHERE LOWER(p.nume) LIKE '%laza%'
      AND r.analiza_standard_id IS NULL
    ORDER BY r.buletin_id, r.id
""")
nemapate = cur.fetchall()

import re
# Pattern gunoi OCR
_GUNOI = re.compile(
    r"^['\"\[\]{}|]|"
    r"Bacteriurie\s*[:<(]|Leucociturie\s*[:<(]|"
    r"Interpretare\s+(rezultat|valori)|"
    r"3-10\s+U/ml|posibila\s+intoleranta|incidenta\s+scazuta|"
    r"testare\s+corecta|obligatoriu\s+pe\s+nemancate|absenta\s+oricarei|"
    r"Glicemie\s+bazala|Normal:|Optim:|crescute?\s*[:<>]|"
    r"eGFR:\s*\d",
    re.IGNORECASE
)

def _e_gunoi_ocr_db(raw: str) -> bool:
    if not raw:
        return False
    raw = raw.strip()
    if _GUNOI.match(raw):
        return True
    # Siruri de silabe/litere scurte
    cuvinte = raw.split()
    if len(cuvinte) >= 4:
        scurte = sum(1 for c in cuvinte if len(re.sub(r'[^a-zA-ZăâîșțĂÂÎȘȚ]', '', c)) <= 2)
        if scurte / len(cuvinte) > 0.55:
            return True
        litere_unice = re.findall(r'\b[a-zA-ZăâîșțĂÂÎȘȚ]\b', raw)
        if len(litere_unice) >= 5 and len(litere_unice) / len(cuvinte) > 0.4:
            return True
    # Fraze lungi administrative (>100 chars cu cuvinte comune, nu medicale)
    if len(raw) > 100 and not re.search(r'\b(hemoglobin|eritrocit|leucocit|glucoz|creatinin|colesterol|vitamina|feritina|anticorp)\b', raw, re.I):
        return True
    return False

de_sters = []
for r in nemapate:
    if _e_gunoi_ocr_db(r['denumire_raw']):
        de_sters.append(r['id'])
        print(f"  GUNOI [{r['buletin_id']}]: {r['denumire_raw'][:70]!r}")

if de_sters:
    cur2.execute(f"DELETE FROM rezultate_analize WHERE id = ANY(%s)", (de_sters,))
    print(f"\nSterse {len(de_sters)} intrari gunoi OCR")
else:
    print("Niciun gunoi de sters")

conn.commit()
conn.close()
print("\nGata!")
