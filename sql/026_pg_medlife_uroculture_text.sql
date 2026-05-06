-- Migrare 026: MedLife / VLADASEL-style — texte urocultură + sediment fără migrările 023/024
-- Idempotent: ON CONFLICT pentru standarde și aliasuri.

-- ─── Standarde sediment (dacă lipsește 023) ───────────────────────────────────
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('CILINDRI_URINA',  'Cilindri urinari'),
('CRISTALE_URINA',  'Cristale urinare'),
('FUNGI_URINA',     'Fungi (sediment urinar)')
ON CONFLICT (cod_standard) DO NOTHING;

-- ─── Aliasuri sediment MedLife (denumiri din buletin / OCR) ─────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindrii hialini' FROM analiza_standard WHERE cod_standard = 'CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindri hialini' FROM analiza_standard WHERE cod_standard = 'CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindri patologici' FROM analiza_standard WHERE cod_standard = 'CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cilindrii patologici' FROM analiza_standard WHERE cod_standard = 'CILINDRI_URINA' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cristale de oxalat de calciu' FROM analiza_standard WHERE cod_standard = 'CRISTALE_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cristale fosfat amoniaco-magnezian' FROM analiza_standard WHERE cod_standard = 'CRISTALE_URINA' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Levuri' FROM analiza_standard WHERE cod_standard = 'FUNGI_URINA' ON CONFLICT (alias) DO NOTHING;

-- ─── Texte descriptive urocultură ─────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Rezultat cantitativ: Bacteriurie'
FROM analiza_standard WHERE cod_standard = 'UROCULTURA'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Organisme absente'
FROM analiza_standard WHERE cod_standard = 'UROCULTURA'
ON CONFLICT (alias) DO NOTHING;
