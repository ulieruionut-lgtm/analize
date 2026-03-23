-- Optimizari simple pentru lista de pacienti (ordonare/paginare)
CREATE INDEX IF NOT EXISTS idx_pacienti_nume ON pacienti(nume);
CREATE INDEX IF NOT EXISTS idx_pacienti_nume_prenume ON pacienti(nume, prenume);
