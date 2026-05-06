-- Migrare 015 PostgreSQL: aceleași coduri/alias-uri ca 015_alias_clinice_necunoscute.sql

INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('FLORA_URINA', 'Flora microbiana urina'),
('MICRO_CULT_FUNGI', 'Cultura fungi'),
('MICRO_EXAM_MIC', 'Examen microbiologic'),
('MICRO_CULT_BACT', 'Culturi bacteriene'),
('MICRO_MICR_COL', 'Examen microscopic colorat'),
('MICRO_CITO_VAG', 'Examen citobacteriologic secretie vaginala'),
('MICRO_AG_CHLAM', 'Ag Chlamydia trachomatis'),
('MICRO_MYCO_UREA', 'Mycoplasma / Ureaplasma'),
('MICRO_CANDIDA_SPP', 'Candida spp')
ON CONFLICT (cod_standard) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'eGFR' FROM analiza_standard WHERE cod_standard='EGFR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'eGFR CKD-EPI' FROM analiza_standard WHERE cod_standard='EGFR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RFG' FROM analiza_standard WHERE cod_standard='EGFR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RFG estimat' FROM analiza_standard WHERE cod_standard='EGFR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Rata de filtrare glomerulara' FROM analiza_standard WHERE cod_standard='EGFR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Rata de filtrare glomerulară' FROM analiza_standard WHERE cod_standard='EGFR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Filtrare glomerulara' FROM analiza_standard WHERE cod_standard='EGFR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'GFR' FROM analiza_standard WHERE cod_standard='EGFR' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Tiroxina serica libera' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Tiroxină serică liberă' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Tiroxina libera' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Tiroxină liberă' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FT4 – Tiroxină serică liberă' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FT4 - Tiroxina serica libera' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina' FROM analiza_standard WHERE cod_standard='BILIRUBIN_TOT' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoza' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoză' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glicemie serica' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glicemie serică' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Feritină' FROM analiza_standard WHERE cod_standard='FERITINA' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'VSH (viteza de sedimentare)' FROM analiza_standard WHERE cod_standard='VSH' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mucus' FROM analiza_standard WHERE cod_standard='URINA_SUMAR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mucus absent' FROM analiza_standard WHERE cod_standard='URINA_SUMAR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mucus prezent' FROM analiza_standard WHERE cod_standard='URINA_SUMAR' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Flora microbiana' FROM analiza_standard WHERE cod_standard='FLORA_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Flora microbiană' FROM analiza_standard WHERE cod_standard='FLORA_URINA' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cultura fungi' FROM analiza_standard WHERE cod_standard='MICRO_CULT_FUNGI' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cultura fungi (mucoase)' FROM analiza_standard WHERE cod_standard='MICRO_CULT_FUNGI' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cultura fungi mucoase' FROM analiza_standard WHERE cod_standard='MICRO_CULT_FUNGI' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Examen microbiologic' FROM analiza_standard WHERE cod_standard='MICRO_EXAM_MIC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Examen microbiologic secretie col' FROM analiza_standard WHERE cod_standard='MICRO_EXAM_MIC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Examen microbiologic secreție col' FROM analiza_standard WHERE cod_standard='MICRO_EXAM_MIC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Examen microbiologic secretie' FROM analiza_standard WHERE cod_standard='MICRO_EXAM_MIC' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Culturi bacteriene' FROM analiza_standard WHERE cod_standard='MICRO_CULT_BACT' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Examen microscopic colorat' FROM analiza_standard WHERE cod_standard='MICRO_MICR_COL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ex. microscopic colorat' FROM analiza_standard WHERE cod_standard='MICRO_MICR_COL' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Examen citobacteriologic secretie vaginala' FROM analiza_standard WHERE cod_standard='MICRO_CITO_VAG' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Examen citobacteriologic secreție vaginală' FROM analiza_standard WHERE cod_standard='MICRO_CITO_VAG' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ag Chlamydia trachomatis' FROM analiza_standard WHERE cod_standard='MICRO_AG_CHLAM' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Chlamydia trachomatis' FROM analiza_standard WHERE cod_standard='MICRO_AG_CHLAM' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ag. Chlamydia trachomatis' FROM analiza_standard WHERE cod_standard='MICRO_AG_CHLAM' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mycoplasma hominis' FROM analiza_standard WHERE cod_standard='MICRO_MYCO_UREA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ureaplasma spp' FROM analiza_standard WHERE cod_standard='MICRO_MYCO_UREA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ureaplasma' FROM analiza_standard WHERE cod_standard='MICRO_MYCO_UREA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mycoplasma / Ureaplasma' FROM analiza_standard WHERE cod_standard='MICRO_MYCO_UREA' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Candida spp' FROM analiza_standard WHERE cod_standard='MICRO_CANDIDA_SPP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Candida spp.' FROM analiza_standard WHERE cod_standard='MICRO_CANDIDA_SPP' ON CONFLICT (alias) DO NOTHING;
