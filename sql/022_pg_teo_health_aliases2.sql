-- Migrare 022: Aliases TEO HEALTH – al doilea buletin (AUREL-NICOLAE-SORIN, 22.12.2025)
-- Acoperă: Lipide, Electroforeza proteine, Markeri tumorali, Ioni serici, RAC urinar

-- ─── Standarde noi ────────────────────────────────────────────────────────────
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('ELECTRO_BETA',  'Electroforeza – Beta globulina totala'),
('RAC_URINA',     'RAC – Raport albumina/creatinina urinara')
ON CONFLICT (cod_standard) DO NOTHING;

-- ─── Trigliceride serice (forma lunga TEO HEALTH) ─────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Trigliceride serice' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE' ON CONFLICT (alias) DO NOTHING;

-- ─── LDL / HDL (forma scurta fara "colesterol") ───────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HDL' FROM analiza_standard WHERE cod_standard='HDL' ON CONFLICT (alias) DO NOTHING;

-- ─── Potasiu si Sodiu cu specificatia (seric) ─────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Potasiu (seric)' FROM analiza_standard WHERE cod_standard='POTASIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Sodiu (seric)' FROM analiza_standard WHERE cod_standard='SODIU' ON CONFLICT (alias) DO NOTHING;

-- ─── Electroforeza – format TEO HEALTH cu % lipit ─────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumina%' FROM analiza_standard WHERE cod_standard='ELECTRO_ALB' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alfa1-globuline%' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA1' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alfa2-globuline%' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA2' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Beta-globuline%' FROM analiza_standard WHERE cod_standard='ELECTRO_BETA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '* Beta1-globuline%' FROM analiza_standard WHERE cod_standard='ELECTRO_BETA1' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '* Beta2-globuline%' FROM analiza_standard WHERE cod_standard='ELECTRO_BETA2' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gamma-globuline%' FROM analiza_standard WHERE cod_standard='ELECTRO_GAMA' ON CONFLICT (alias) DO NOTHING;

-- ─── Raport albumine/globuline (RAPORT_AG) ────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Raport albumine/globuline' FROM analiza_standard WHERE cod_standard='RAPORT_AG' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Raport albumina/globuline' FROM analiza_standard WHERE cod_standard='RAPORT_AG' ON CONFLICT (alias) DO NOTHING;

-- ─── RAC (raport albumina/creatinina urinara) ─────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RAC (raport albumina/creatinina urinara)' FROM analiza_standard WHERE cod_standard='RAC_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '* RAC (raport albumina/creatinina urinara)' FROM analiza_standard WHERE cod_standard='RAC_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RAC' FROM analiza_standard WHERE cod_standard='RAC_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Raport albumina/creatinina urinara' FROM analiza_standard WHERE cod_standard='RAC_URINA' ON CONFLICT (alias) DO NOTHING;
