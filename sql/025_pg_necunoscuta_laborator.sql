-- Context laborator pe analize necunoscute (auto-rezolvare + filtru fuzzy per catalog).
ALTER TABLE analiza_necunoscuta ADD COLUMN IF NOT EXISTS laborator_id INTEGER REFERENCES laboratoare(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_analiza_necunoscuta_laborator ON analiza_necunoscuta(laborator_id);
