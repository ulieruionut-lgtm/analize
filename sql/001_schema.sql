-- Schema PostgreSQL pentru MVP analize medicale

-- Pacienți (identificați unic după CNP)
CREATE TABLE IF NOT EXISTS pacienti (
    id SERIAL PRIMARY KEY,
    cnp VARCHAR(13) UNIQUE NOT NULL,
    nume VARCHAR(255) NOT NULL,
    prenume VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analize standard (categorii normalizate)
CREATE TABLE IF NOT EXISTS analiza_standard (
    id SERIAL PRIMARY KEY,
    cod_standard VARCHAR(64) UNIQUE NOT NULL,
    denumire_standard VARCHAR(255) NOT NULL
);

-- Alias-uri pentru mapare la analiza standard (Glucoză, Glucose, Glicemie etc.)
CREATE TABLE IF NOT EXISTS analiza_alias (
    id SERIAL PRIMARY KEY,
    analiza_standard_id INTEGER NOT NULL REFERENCES analiza_standard(id) ON DELETE CASCADE,
    alias VARCHAR(255) NOT NULL,
    UNIQUE(alias)
);

-- Buletine / fișiere PDF încărcate
CREATE TABLE IF NOT EXISTS buletine (
    id SERIAL PRIMARY KEY,
    pacient_id INTEGER NOT NULL REFERENCES pacienti(id) ON DELETE CASCADE,
    data_buletin TIMESTAMPTZ,
    laborator VARCHAR(255),
    fisier_original VARCHAR(512),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Rezultate analize per buletin
CREATE TABLE IF NOT EXISTS rezultate_analize (
    id SERIAL PRIMARY KEY,
    buletin_id INTEGER NOT NULL REFERENCES buletine(id) ON DELETE CASCADE,
    analiza_standard_id INTEGER REFERENCES analiza_standard(id) ON DELETE SET NULL,
    denumire_raw VARCHAR(255),
    valoare NUMERIC,
    valoare_text TEXT,
    unitate VARCHAR(64),
    interval_min NUMERIC,
    interval_max NUMERIC,
    flag VARCHAR(16),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pacienti_cnp ON pacienti(cnp);
CREATE INDEX IF NOT EXISTS idx_buletine_pacient ON buletine(pacient_id);
CREATE INDEX IF NOT EXISTS idx_rezultate_buletin ON rezultate_analize(buletin_id);
CREATE INDEX IF NOT EXISTS idx_rezultate_analiza_standard ON rezultate_analize(analiza_standard_id);
