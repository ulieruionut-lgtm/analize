-- Alias-uri din cataloage laboratoare (Synevo, MedLife, Regina Maria, etc.)
-- Denumiri alternative folosite in buletine pentru recunoastere la parsare

-- Synevo / alte lab: Hemoleucograma (sectiune) - nu mapam la o analiza, doar alias-uri pentru parametri
-- Eritrocite = RBC (Synevo, MedLife)
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eritrocite' FROM analiza_standard WHERE cod_standard='RBC';

-- Creatinina (fara diacritics) - multi lab
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina' FROM analiza_standard WHERE cod_standard='CREATININA';

-- Proteina C reactiva (fara diacritics)
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteina C reactiva' FROM analiza_standard WHERE cod_standard='CRP';
