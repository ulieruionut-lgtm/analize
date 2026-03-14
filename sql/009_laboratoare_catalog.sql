-- Migrare 009: tabel laboratoare + catalog analize per laborator
-- PostgreSQL: ruleaza din run_migrations.py
-- SQLite: ruleaza la startup din main.py

-- Tabel laboratoare (retele nationale/regionale)
CREATE TABLE IF NOT EXISTS laboratoare (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nume VARCHAR(255) NOT NULL UNIQUE,
    website VARCHAR(512),
    retea VARCHAR(255),
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_laboratoare_nume ON laboratoare(nume);

-- Tabel laborator_analize: ce analize ofera fiecare lab
CREATE TABLE IF NOT EXISTS laborator_analize (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    laborator_id INTEGER NOT NULL REFERENCES laboratoare(id) ON DELETE CASCADE,
    analiza_standard_id INTEGER NOT NULL REFERENCES analiza_standard(id) ON DELETE CASCADE,
    UNIQUE(laborator_id, analiza_standard_id)
);
CREATE INDEX IF NOT EXISTS idx_laborator_analize_lab ON laborator_analize(laborator_id);
CREATE INDEX IF NOT EXISTS idx_laborator_analize_std ON laborator_analize(analiza_standard_id);
