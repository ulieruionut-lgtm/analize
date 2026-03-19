-- Migrare 011: rezultate descriptive (microbiologie MedLife, paragrafe OCR)
-- Înainte: VARCHAR(128) → eroare „value too long for type character varying(128)”

ALTER TABLE rezultate_analize
    ALTER COLUMN valoare_text TYPE TEXT USING valoare_text::TEXT;
