-- Migrare 007: adauga coloane ordine si categorie in rezultate_analize
-- Permite afisarea analizelor in ordinea si pe sectiunile din buletinul original

ALTER TABLE rezultate_analize
    ADD COLUMN IF NOT EXISTS ordine INTEGER DEFAULT NULL;

ALTER TABLE rezultate_analize
    ADD COLUMN IF NOT EXISTS categorie VARCHAR(100) DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_rezultate_ordine ON rezultate_analize(buletin_id, ordine);
CREATE INDEX IF NOT EXISTS idx_rezultate_categorie ON rezultate_analize(buletin_id, categorie);
