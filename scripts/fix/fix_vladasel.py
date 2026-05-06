"""
Corecteaza valorile eronate pentru Vladasel in DB (HGB 4.0->14, HCT 4.1->44 etc.)
Ruleaza o singura data.
"""
import os, sys, psycopg2, psycopg2.extras
sys.stdout.reconfigure(encoding="utf-8")
DB = os.environ.get("DATABASE_URL", "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL@shortline.proxy.rlwy.net:17411/railway")

conn = psycopg2.connect(DB)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Buletine Vladasel
cur.execute("""
    SELECT r.id, r.denumire_raw, r.valoare, r.unitate, a.denumire_standard, a.cod_standard
    FROM rezultate_analize r
    LEFT JOIN analiza_standard a ON a.id = r.analiza_standard_id
    WHERE r.buletin_id IN (SELECT id FROM buletine WHERE pacient_id IN (
        SELECT id FROM pacienti WHERE LOWER(nume) = 'vladasel'
    ))
""")
rows = cur.fetchall()

corectii = []
for row in rows:
    rid, raw, val, u, std, cod = row["id"], row["denumire_raw"], row["valoare"], row["unitate"], row["denumire_standard"], row["cod_standard"]
    u = (u or "").lower()
    raw_l = (raw or "").lower()

    new_val = None
    # HCT 4.1 -> 44.1 (valorile 3.5-5.5 inmultite cu 10)
    if val and (cod == "HCT" or "hematocrit" in raw_l or "hct" in raw_l):
        if u == "%" and 3.5 <= val <= 5.5:
            new_val = val * 10
    # HGB 4.0 -> 14.0 (cifra 1 pierduta)
    if val and (cod == "HB" or "hemoglobin" in raw_l or "hgb" in raw_l):
        if "g/dl" in u and 4.0 <= val <= 4.5:
            new_val = val + 10

    if new_val is not None:
        corectii.append((rid, val, new_val, raw[:50]))

for rid, old_v, new_v, raw in corectii:
    cur.execute("UPDATE rezultate_analize SET valoare = %s WHERE id = %s", (new_v, rid))
    print(f"  id={rid}: {raw}... {old_v} -> {new_v}")

conn.commit()
print(f"\nCorectate {len(corectii)} valori.")
conn.close()
