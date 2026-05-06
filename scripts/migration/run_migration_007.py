"""Rulare migrare 007: adauga coloane ordine si categorie in rezultate_analize."""
import psycopg2

DB_URL = (
    "postgresql://postgres:qwgRDQgrXiMkhtzncTUEuCdcszDlPipL"
    "@shortline.proxy.rlwy.net:17411/railway"
)

sql = """
ALTER TABLE rezultate_analize
    ADD COLUMN IF NOT EXISTS ordine INTEGER DEFAULT NULL;

ALTER TABLE rezultate_analize
    ADD COLUMN IF NOT EXISTS categorie VARCHAR(100) DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_rezultate_ordine ON rezultate_analize(buletin_id, ordine);
CREATE INDEX IF NOT EXISTS idx_rezultate_categorie ON rezultate_analize(buletin_id, categorie);
"""

conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()
for stmt in sql.strip().split(";"):
    stmt = stmt.strip()
    if stmt:
        try:
            cur.execute(stmt)
            print(f"OK: {stmt[:80]}")
        except Exception as e:
            print(f"ERR: {e}")
conn.close()
print("Done.")
