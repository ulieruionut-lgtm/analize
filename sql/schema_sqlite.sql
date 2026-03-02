-- Schema SQLite pentru MVP (fără configurare)

CREATE TABLE IF NOT EXISTS pacienti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cnp TEXT UNIQUE NOT NULL,
    nume TEXT NOT NULL,
    prenume TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS analiza_standard (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_standard TEXT UNIQUE NOT NULL,
    denumire_standard TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analiza_alias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analiza_standard_id INTEGER NOT NULL REFERENCES analiza_standard(id) ON DELETE CASCADE,
    alias TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS buletine (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pacient_id INTEGER NOT NULL REFERENCES pacienti(id) ON DELETE CASCADE,
    data_buletin TEXT,
    laborator TEXT,
    fisier_original TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rezultate_analize (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buletin_id INTEGER NOT NULL REFERENCES buletine(id) ON DELETE CASCADE,
    analiza_standard_id INTEGER REFERENCES analiza_standard(id) ON DELETE SET NULL,
    denumire_raw TEXT,
    valoare REAL,
    valoare_text TEXT,
    unitate TEXT,
    interval_min REAL,
    interval_max REAL,
    flag TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_pacienti_cnp ON pacienti(cnp);
CREATE INDEX IF NOT EXISTS idx_buletine_pacient ON buletine(pacient_id);
CREATE INDEX IF NOT EXISTS idx_rezultate_buletin ON rezultate_analize(buletin_id);
CREATE INDEX IF NOT EXISTS idx_rezultate_analiza_standard ON rezultate_analize(analiza_standard_id);
