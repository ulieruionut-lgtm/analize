-- Migrare 023: Sediment urinar – parametri individuali TEO HEALTH
-- Acoperă: Celule epiteliale, Cilindri, Bacterii, Fungi, Cristale, Mucus (sediment)
-- NOTA: aliasuri scurte comune ('Glucoza', 'Eritrocite', etc.) nu sunt adaugate
-- deoarece sunt deja alias pentru standardele serice; necesita disambiguare pe categorie.

-- ─── Standarde noi ────────────────────────────────────────────────────────────
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('CELULE_EPITELIALE',  'Celule epiteliale (sediment urinar)'),
('CILINDRI_URINA',     'Cilindri urinari'),
('BACTERII_URINA',     'Bacterii (sediment urinar)'),
('FUNGI_URINA',        'Fungi (sediment urinar)'),
('CRISTALE_URINA',     'Cristale urinare'),
('MUCUS_URINA',        'Mucus urinar')
ON CONFLICT (cod_standard) DO NOTHING;

-- ─── Celule epiteliale ─────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Celule epiteliale' FROM analiza_standard WHERE cod_standard='CELULE_EPITELIALE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Celule epiteliale plate' FROM analiza_standard WHERE cod_standard='CELULE_EPITELIALE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Celule epiteliale tubulare' FROM analiza_standard WHERE cod_standard='CELULE_EPITELIALE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Celule epiteliale /camp' FROM analiza_standard WHERE cod_standard='CELULE_EPITELIALE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Celule epiteliale/camp' FROM analiza_standard WHERE cod_standard='CELULE_EPITELIALE' ON CONFLICT (alias) DO NOTHING;

-- ─── Cilindri urinari ──────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindri' FROM analiza_standard WHERE cod_standard='CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindri hialini' FROM analiza_standard WHERE cod_standard='CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindri granulosi' FROM analiza_standard WHERE cod_standard='CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindri urinari' FROM analiza_standard WHERE cod_standard='CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindri /camp' FROM analiza_standard WHERE cod_standard='CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;

-- ─── Bacterii ─────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bacterii' FROM analiza_standard WHERE cod_standard='BACTERII_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bacterii (sediment)' FROM analiza_standard WHERE cod_standard='BACTERII_URINA' ON CONFLICT (alias) DO NOTHING;

-- ─── Fungi ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fungi' FROM analiza_standard WHERE cod_standard='FUNGI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fungi (sediment)' FROM analiza_standard WHERE cod_standard='FUNGI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Levuri' FROM analiza_standard WHERE cod_standard='FUNGI_URINA' ON CONFLICT (alias) DO NOTHING;

-- ─── Cristale ─────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cristale' FROM analiza_standard WHERE cod_standard='CRISTALE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cristale urinare' FROM analiza_standard WHERE cod_standard='CRISTALE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alte cristale' FROM analiza_standard WHERE cod_standard='CRISTALE_URINA' ON CONFLICT (alias) DO NOTHING;

-- ─── Mucus ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mucus' FROM analiza_standard WHERE cod_standard='MUCUS_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mucus (sediment)' FROM analiza_standard WHERE cod_standard='MUCUS_URINA' ON CONFLICT (alias) DO NOTHING;

-- ─── Eritrocite + Leucocite – aliasuri suplimentare cu /camp ──────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eritrocite/camp' FROM analiza_standard WHERE cod_standard='ERITROCITE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eritrocite /camp' FROM analiza_standard WHERE cod_standard='ERITROCITE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Leucocite/camp' FROM analiza_standard WHERE cod_standard='LEUCOCITE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Leucocite /camp' FROM analiza_standard WHERE cod_standard='LEUCOCITE_URINA' ON CONFLICT (alias) DO NOTHING;
