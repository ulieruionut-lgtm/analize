-- Alias-uri din cataloage laboratoare (Synevo, MedLife, Regina Maria, etc.)
-- PostgreSQL: ON CONFLICT (alias) DO NOTHING

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eritrocite' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina' FROM analiza_standard WHERE cod_standard='CREATININA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteina C reactiva' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;
