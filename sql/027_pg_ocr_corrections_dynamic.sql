-- Migrare 027: tabel corecții OCR dinamice (fără redeploy)
-- Permite adăugarea de corecții OCR din UI admin, persistate în DB.
CREATE TABLE IF NOT EXISTS ocr_corrections_db (
    id SERIAL PRIMARY KEY,
    tip VARCHAR(20) NOT NULL DEFAULT 'direct',     -- 'direct' (substring) | 'regex'
    domeniu VARCHAR(30),                            -- NULL = global; ex: 'hematology', 'urine', 'biochemistry'
    pattern TEXT NOT NULL,
    replacement TEXT NOT NULL,
    activ BOOLEAN NOT NULL DEFAULT TRUE,
    prioritate INTEGER NOT NULL DEFAULT 100,        -- mai mic = aplicat primul
    sursa VARCHAR(50) DEFAULT 'manual',             -- 'manual' | 'llm_auto'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ocr_corrections_activ ON ocr_corrections_db (activ, prioritate);
