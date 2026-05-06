-- Migrare 014: metadata structurată (microbiologie: organism_raw, rezultat_tip) ca JSON text
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rezultate_analize' AND column_name = 'rezultat_meta'
    ) THEN
        ALTER TABLE rezultate_analize ADD COLUMN rezultat_meta TEXT;
    END IF;
END $$;
