import psycopg2, psycopg2.extras
DB = "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway"
conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

ALIASURI = [
    ("_UROBILINOGEN", 290),
    ("_UROBILINOGEN,", 290),
    ("_UROBILINOGEN,, E | E", 290),
    ("NITRITI,", 291),
    ('NITRITI, "negativ', 291),
    ("Nitriti", 291),
]

for alias, sid in ALIASURI:
    cur.execute(
        "INSERT INTO analiza_alias (analiza_standard_id, alias) VALUES (%s, %s) ON CONFLICT (alias) DO NOTHING",
        (sid, alias)
    )
    status = "+" if cur.rowcount else "="
    print(f"  {status} '{alias}'")

conn.commit()
conn.close()
print("OK")
