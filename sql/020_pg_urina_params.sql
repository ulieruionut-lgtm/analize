-- Migrare 020: Parametri individuali sumar urinar Bioclinica
-- pH, Densitate, Corpi cetonici, Nitriti, Urobilinogen + variante urinare
-- pentru Leucocite/Eritrocite/Glucoza/Proteine/Bilirubina distincte de cele serice

INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('PH_URINA',         'pH urinar'),
('DENSITATE_URINA',  'Densitate urinara'),
('CORPI_CETONICI',   'Corpi cetonici'),
('NITRITI_URINA',    'Nitriti urinari'),
('UROBILINOGEN',     'Urobilinogen'),
('PROTEINE_URINA',   'Proteine urinare'),
('GLUCOZA_URINA',    'Glucoza urinara'),
('BILIRUBINA_URINA', 'Bilirubina urinara'),
('LEUCOCITE_URINA',  'Leucocite urinare'),
('ERITROCITE_URINA', 'Eritrocite urinare')
ON CONFLICT (cod_standard) DO NOTHING;

-- pH urinar
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'pH' FROM analiza_standard WHERE cod_standard='PH_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PH' FROM analiza_standard WHERE cod_standard='PH_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'pH urinar' FROM analiza_standard WHERE cod_standard='PH_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'pH urina' FROM analiza_standard WHERE cod_standard='PH_URINA' ON CONFLICT (alias) DO NOTHING;

-- Densitate urinara
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Densitate' FROM analiza_standard WHERE cod_standard='DENSITATE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Densitate urinara' FROM analiza_standard WHERE cod_standard='DENSITATE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Densitate urinară' FROM analiza_standard WHERE cod_standard='DENSITATE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Densitate relativa' FROM analiza_standard WHERE cod_standard='DENSITATE_URINA' ON CONFLICT (alias) DO NOTHING;

-- Corpi cetonici
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Corpi cetonici' FROM analiza_standard WHERE cod_standard='CORPI_CETONICI' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Corpi cetonici (urina)' FROM analiza_standard WHERE cod_standard='CORPI_CETONICI' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cetone' FROM analiza_standard WHERE cod_standard='CORPI_CETONICI' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cetone urina' FROM analiza_standard WHERE cod_standard='CORPI_CETONICI' ON CONFLICT (alias) DO NOTHING;

-- Nitriti urinari
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nitriti' FROM analiza_standard WHERE cod_standard='NITRITI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nitriți' FROM analiza_standard WHERE cod_standard='NITRITI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nitriti urinari' FROM analiza_standard WHERE cod_standard='NITRITI_URINA' ON CONFLICT (alias) DO NOTHING;

-- Urobilinogen
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Urobilinogen' FROM analiza_standard WHERE cod_standard='UROBILINOGEN' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Urobilinogen urinar' FROM analiza_standard WHERE cod_standard='UROBILINOGEN' ON CONFLICT (alias) DO NOTHING;

-- Proteine urinare (forma lunga — forma scurta e rezolvata prin override de categorie)
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteine urinare' FROM analiza_standard WHERE cod_standard='PROTEINE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteine (urina)' FROM analiza_standard WHERE cod_standard='PROTEINE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Microalbumina urinara' FROM analiza_standard WHERE cod_standard='PROTEINE_URINA' ON CONFLICT (alias) DO NOTHING;

-- Glucoza urinara (forma lunga — forma scurta e rezolvata prin override de categorie)
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoza urinara' FROM analiza_standard WHERE cod_standard='GLUCOZA_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoza (urina)' FROM analiza_standard WHERE cod_standard='GLUCOZA_URINA' ON CONFLICT (alias) DO NOTHING;

-- Bilirubina urinara (forma lunga — forma scurta e rezolvata prin override de categorie)
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina urinara' FROM analiza_standard WHERE cod_standard='BILIRUBINA_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina (urina)' FROM analiza_standard WHERE cod_standard='BILIRUBINA_URINA' ON CONFLICT (alias) DO NOTHING;

-- Leucocite urinare (forma lunga — forma scurta e rezolvata prin override de categorie)
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Leucocite urinare' FROM analiza_standard WHERE cod_standard='LEUCOCITE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Leucocite (urina)' FROM analiza_standard WHERE cod_standard='LEUCOCITE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Leucocite sediment' FROM analiza_standard WHERE cod_standard='LEUCOCITE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Leucocite/camp' FROM analiza_standard WHERE cod_standard='LEUCOCITE_URINA' ON CONFLICT (alias) DO NOTHING;

-- Eritrocite urinare (forma lunga — forma scurta e rezolvata prin override de categorie)
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eritrocite urinare' FROM analiza_standard WHERE cod_standard='ERITROCITE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eritrocite (urina)' FROM analiza_standard WHERE cod_standard='ERITROCITE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eritrocite sediment' FROM analiza_standard WHERE cod_standard='ERITROCITE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hematii (urina)' FROM analiza_standard WHERE cod_standard='ERITROCITE_URINA' ON CONFLICT (alias) DO NOTHING;
