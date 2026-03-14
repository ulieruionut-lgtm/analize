-- Alias-uri pentru variatii OCR (umar->Numar, truncari) - Laza si alte buletine scanate
-- Ruleaza: psql $DATABASE_URL -f sql/006_pg_alias_ocr.sql

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'umar de eozinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'umar de eozinofile (EOS)' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'umar de neutrofile' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de neutrofile (NEUT) :' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'umar de bazofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'umar de limfocite' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'umar de monocite' FROM analiza_standard WHERE cod_standard='MONOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'umar de trombocite' FROM analiza_standard WHERE cod_standard='PLT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'umar de eritrocite' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'umar de leucocite' FROM analiza_standard WHERE cod_standard='WBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Largimea distributiei eritrocitare - coe' FROM analiza_standard WHERE cod_standard='RDW' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Largimea distributiei eritrocitare - coeficient' FROM analiza_standard WHERE cod_standard='RDW' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Distributia plachetelor(trombocitelor) (' FROM analiza_standard WHERE cod_standard='PDW' ON CONFLICT (alias) DO NOTHING;
