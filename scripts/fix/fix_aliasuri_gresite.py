import sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding='utf-8')
DB_URL = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── 1. Sterge aliasuri gresite adaugate (OCR garbage sau mapare incorecta) ───
print("1. STERG aliasuri gresite/confuze:")
aliasuri_gresite = [
    # Creatinina urinara pointand la Creatinina serica - GRESIT
    '1.4.12 * Creatinina urinara',
    '2 * RAC (raport albumina/creatinina urinara)',
    '91:42 * Creatinina urinara',
    '- Clearance la creatinina*',
    # Calciu urinar pointand la Calciu seric - GRESIT
    '1.1.14 * Calciu urinar',
    # Fragmente cu numere/prefix OCR - Bazofile nr -> % e gresit
    'Bazofile 40/mm³',
    'Bazofile 50/mm³',
    'Eozinofile 480/mm³',
    'Eozinofile 60/mm³',
    'Limfocite 1.150/mm³',
    'Limfocite 2.410/mm³',
    'Monocite 440/mm³',
    'Monocite 460/mm³',
    'Neutrofile 2.260/mm³',
    'Neutrofile 3.070/mm³',
    # Fragmente cu data in raw - sunt specifice unui buletin, nu general
    'Creatinină serică 10.02.2025',
    'Fier seric (sideremie) 15.04.2024',
    'Glucoză 15.04.2024',
    'FT4 (tiroxina liberă) 15.04.2024',
    'TSH (hormon hipofizar tireostimulator bazal) 15.04.2024',
    # Prefix garbage
    '7, Calciu ionic seric',
    '1;2 HGB (Hemoglobina)',
    '4:10 Limfocite%',
    '+11 Monocite %',
    'E HDL colesterol',
]
sterse = 0
for alias in aliasuri_gresite:
    cur.execute("DELETE FROM analiza_alias WHERE LOWER(alias)=LOWER(%s)", (alias,))
    if cur.rowcount > 0:
        print(f"   STERS: '{alias}'")
        sterse += 1
    else:
        print(f"   NU EXISTA: '{alias}'")
print(f"   Total sterse: {sterse}")

# ── 2. Adauga aliasuri CORECTE pentru ce a ramas ────────────────────────────
print("\n2. Adaug aliasuri corecte:")
# Bazofile /mm³ -> Bazofile numar absolut (nu %)
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='BAS_NR'")
bas_nr = cur.fetchone()
if bas_nr:
    for alias in ['Bazofile 40/mm³', 'Bazofile 50/mm³']:
        cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (alias, bas_nr['id']))
        if cur.rowcount > 0: print(f"   NOU (BAS_NR): '{alias}'")

# Eozinofile /mm³ -> Eozinofile numar absolut
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='EOS_NR'")
eos_nr = cur.fetchone()
if eos_nr:
    for alias in ['Eozinofile 480/mm³', 'Eozinofile 60/mm³']:
        cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (alias, eos_nr['id']))
        if cur.rowcount > 0: print(f"   NOU (EOS_NR): '{alias}'")

# Limfocite /mm³ -> Limfocite numar absolut
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='LYM_NR'")
lym_nr = cur.fetchone()
if lym_nr:
    for alias in ['Limfocite 1.150/mm³', 'Limfocite 2.410/mm³']:
        cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (alias, lym_nr['id']))
        if cur.rowcount > 0: print(f"   NOU (LYM_NR): '{alias}'")

# Monocite /mm³ -> Monocite numar absolut
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='MON_NR'")
mon_nr = cur.fetchone()
if mon_nr:
    for alias in ['Monocite 440/mm³', 'Monocite 460/mm³']:
        cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (alias, mon_nr['id']))
        if cur.rowcount > 0: print(f"   NOU (MON_NR): '{alias}'")

# Neutrofile /mm³ -> Neutrofile numar absolut
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='NEU_NR'")
neu_nr = cur.fetchone()
if neu_nr:
    for alias in ['Neutrofile 2.260/mm³', 'Neutrofile 3.070/mm³']:
        cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (alias, neu_nr['id']))
        if cur.rowcount > 0: print(f"   NOU (NEU_NR): '{alias}'")

# Calciu urinar -> mapare corecta la Calciu seric pana cand avem standard separat
cur.execute("SELECT id FROM analiza_standard WHERE cod_standard='CA'")
ca_std = cur.fetchone()
if ca_std:
    cur.execute("INSERT INTO analiza_alias (alias, analiza_standard_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                ('Calciu urinar', ca_std['id']))
    if cur.rowcount > 0: print(f"   NOU: 'Calciu urinar' -> Calciu seric")

# ── 3. Verifica Iancu ────────────────────────────────────────────────────────
print("\n3. Verifica Iancu Gheorghe:")
cur.execute("SELECT id, nume FROM pacienti WHERE LOWER(nume) LIKE '%%iancu%%'")
iancu = cur.fetchone()
if iancu:
    cur.execute("SELECT b.id, b.data_buletin FROM buletine b WHERE b.pacient_id=%s ORDER BY b.data_buletin", (iancu['id'],))
    buletine = cur.fetchall()
    print(f"   Pacient: {iancu['nume']} - {len(buletine)} buletine")
    for b in buletine:
        cur.execute("SELECT COUNT(*) as t, COUNT(analiza_standard_id) as m FROM rezultate_analize WHERE buletin_id=%s", (b['id'],))
        s = cur.fetchone()
        pct = int(s['m']/s['t']*100) if s['t'] > 0 else 0
        status = "✓" if s['m'] == s['t'] else "!!"
        print(f"   {status} B{b['id']} ({b['data_buletin'].date() if b['data_buletin'] else '?'}) | {s['m']}/{s['t']} ({pct}%)")
else:
    print("   Iancu nu exista in DB!")

conn.commit()
cur.execute("SELECT COUNT(*) as n FROM analiza_alias")
print(f"\n=== Total aliasuri finale: {cur.fetchone()['n']} ===")
conn.close()
