-- Alias-uri specifice Bioclinica (din buletine NITU MATEI 13.02.2026, etc.)
-- Ruleaza: inclus in run_migrations.py

-- Hematii = Eritrocite (RBC) - termen folosit de Bioclinica
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hematii' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;

-- Proteina C reactivă (cu diacritics) -> CRP
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteina C reactivă' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;
