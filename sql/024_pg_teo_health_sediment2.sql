-- Migrare 024: TEO HEALTH – aliasuri sediment detaliat si Acid ascorbic
-- Bazat pe buletin AUREL-NICOLAE-SORIN: cristale specifice, celule tranzitionale,
-- flora microbiana, cilindri patologici, Acid ascorbic urinar.

-- ─── Standard nou ─────────────────────────────────────────────────────────────
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('ACID_ASCORBIC_URINA', 'Acid ascorbic urinar (vitamina C)')
ON CONFLICT (cod_standard) DO NOTHING;

-- ─── Acid ascorbic ────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Acid ascorbic' FROM analiza_standard WHERE cod_standard='ACID_ASCORBIC_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '* Acid ascorbic' FROM analiza_standard WHERE cod_standard='ACID_ASCORBIC_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Acid ascorbic urinar' FROM analiza_standard WHERE cod_standard='ACID_ASCORBIC_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamina C (urina)' FROM analiza_standard WHERE cod_standard='ACID_ASCORBIC_URINA' ON CONFLICT (alias) DO NOTHING;

-- ─── Celule epiteliale tranzitionale ──────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Celule epiteliale tranzitionale' FROM analiza_standard WHERE cod_standard='CELULE_EPITELIALE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Celule epiteliale tranziționale' FROM analiza_standard WHERE cod_standard='CELULE_EPITELIALE' ON CONFLICT (alias) DO NOTHING;

-- ─── Cilindri – variante cu dublu 'i' (OCR TEO HEALTH) ────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindrii hialini' FROM analiza_standard WHERE cod_standard='CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindri patologici' FROM analiza_standard WHERE cod_standard='CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindrii patologici' FROM analiza_standard WHERE cod_standard='CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindri waxy' FROM analiza_standard WHERE cod_standard='CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;

-- ─── Cristale specifice ────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cristale de oxalat de calciu' FROM analiza_standard WHERE cod_standard='CRISTALE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cristale acid uric' FROM analiza_standard WHERE cod_standard='CRISTALE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cristale fosfat amoniaco-magnezian' FROM analiza_standard WHERE cod_standard='CRISTALE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cristale amorfe' FROM analiza_standard WHERE cod_standard='CRISTALE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cristale de fosfat de calciu' FROM analiza_standard WHERE cod_standard='CRISTALE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cristale de urati' FROM analiza_standard WHERE cod_standard='CRISTALE_URINA' ON CONFLICT (alias) DO NOTHING;

-- ─── Flora microbiana ─────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Flora microbiana' FROM analiza_standard WHERE cod_standard='BACTERII_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Flora microbiană' FROM analiza_standard WHERE cod_standard='BACTERII_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Flora bacteriana' FROM analiza_standard WHERE cod_standard='BACTERII_URINA' ON CONFLICT (alias) DO NOTHING;
