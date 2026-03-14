-- Migrare 009: tabel laboratoare + catalog analize per laborator (PostgreSQL)

CREATE TABLE IF NOT EXISTS laboratoare (
    id SERIAL PRIMARY KEY,
    nume VARCHAR(255) NOT NULL UNIQUE,
    website VARCHAR(512),
    retea VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_laboratoare_nume ON laboratoare(nume);

CREATE TABLE IF NOT EXISTS laborator_analize (
    id SERIAL PRIMARY KEY,
    laborator_id INTEGER NOT NULL REFERENCES laboratoare(id) ON DELETE CASCADE,
    analiza_standard_id INTEGER NOT NULL REFERENCES analiza_standard(id) ON DELETE CASCADE,
    UNIQUE(laborator_id, analiza_standard_id)
);
CREATE INDEX IF NOT EXISTS idx_laborator_analize_lab ON laborator_analize(laborator_id);
CREATE INDEX IF NOT EXISTS idx_laborator_analize_std ON laborator_analize(analiza_standard_id);
