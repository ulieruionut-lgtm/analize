-- Migrare 012: categorie din buletin (secțiune parser) pentru analize necunoscute
-- Ajută la asociere manuală grupată (Hemoleucogramă, Biochimie, Urină, …)

ALTER TABLE analiza_necunoscuta ADD COLUMN IF NOT EXISTS categorie VARCHAR(100);
