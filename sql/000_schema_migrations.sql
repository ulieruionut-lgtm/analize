-- Tabela pentru versionarea migrarilor aplicate.
-- Aplicata prima, inainte de orice alt fisier SQL.

CREATE TABLE IF NOT EXISTS schema_migrations (
    id          SERIAL PRIMARY KEY,
    versiune    VARCHAR(128) UNIQUE NOT NULL,
    aplicata_la TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pentru lookup rapid
CREATE INDEX IF NOT EXISTS idx_schema_migrations_versiune ON schema_migrations (versiune);
