-- Corecteaza numele corupte din baza de date
-- Ruleaza: railway connect Postgres (dupa care copiaza si executa)

UPDATE pacienti SET nume = 'VLADASEL', prenume = 'ELENA'
WHERE cnp = '2470112080077';

UPDATE pacienti SET nume = 'VLADASEL', prenume = 'AUREL-NICOLAE-SORIN'
WHERE cnp = '1461208080072';

UPDATE pacienti SET nume = 'PETREAN', prenume = 'ANA'
WHERE cnp = '2540207080070';

-- Verifica rezultatul
SELECT cnp, LEFT(nume,50) as nume, LEFT(prenume,30) as prenume FROM pacienti ORDER BY id;
