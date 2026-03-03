-- Migrare 005: alias-uri complete forma lunga + analize standard noi
-- Acopera formatele Bioclinica cu denumiri complete ("Numar de eritrocite (RBC)" etc.)

-- ─── Analize standard noi ────────────────────────────────────────────────────
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('ASLO',    'ASLO – Anticorpi anti-streptolizina O'),
('PTH',     'PTH – Parathormon intact (iPTH)'),
('DAO',     'DAO – Diaminoxidaza'),
('IGE',     'IgE totala'),
('FR',      'Factor reumatoid (FR)'),
('HOMOCIST','Homocisteina serica')
ON CONFLICT (cod_standard) DO NOTHING;

-- ─── Alias-uri forma lunga hemoleucograma (format Bioclinica) ────────────────

-- Eritrocite
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de eritrocite' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar eritrocite' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. de eritrocite' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de eritrocite (RBC)' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;

-- Hemoglobina
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina (HGB)' FROM analiza_standard WHERE cod_standard='HB' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina HGB' FROM analiza_standard WHERE cod_standard='HB' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina (Hb)' FROM analiza_standard WHERE cod_standard='HB' ON CONFLICT (alias) DO NOTHING;

-- Hematocrit
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hematocrit (HCT)' FROM analiza_standard WHERE cod_standard='HCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hematocrit (Ht)' FROM analiza_standard WHERE cod_standard='HCT' ON CONFLICT (alias) DO NOTHING;

-- MCV
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Volumul mediu eritrocitar' FROM analiza_standard WHERE cod_standard='MCV' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Volumul mediu eritrocitar (MCV)' FROM analiza_standard WHERE cod_standard='MCV' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Volum eritrocitar mediu (MCV)' FROM analiza_standard WHERE cod_standard='MCV' ON CONFLICT (alias) DO NOTHING;

-- MCH
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina eritrocitara medie (MCH)' FROM analiza_standard WHERE cod_standard='MCH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina eritrocitara medie' FROM analiza_standard WHERE cod_standard='MCH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HEM (MCH)' FROM analiza_standard WHERE cod_standard='MCH' ON CONFLICT (alias) DO NOTHING;

-- MCHC
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Concentratia medie a hemoglobinei eritrocitare' FROM analiza_standard WHERE cod_standard='MCHC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Concentratia medie a hemoglobinei eritrocitare (MCHC)' FROM analiza_standard WHERE cod_standard='MCHC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Concentratia hemoglobinei eritrocitare' FROM analiza_standard WHERE cod_standard='MCHC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CHEM (MCHC)' FROM analiza_standard WHERE cod_standard='MCHC' ON CONFLICT (alias) DO NOTHING;

-- RDW
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Largimea distributiei eritrocitare' FROM analiza_standard WHERE cod_standard='RDW' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Largimea distributiei eritrocitare - coeficient variatie (RDW-CV)' FROM analiza_standard WHERE cod_standard='RDW' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Largimea distributiei eritrocitare (RDW-CV)' FROM analiza_standard WHERE cod_standard='RDW' ON CONFLICT (alias) DO NOTHING;

-- Leucocite
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de leucocite' FROM analiza_standard WHERE cod_standard='WBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de leucocite (WBC)' FROM analiza_standard WHERE cod_standard='WBC' ON CONFLICT (alias) DO NOTHING;

-- Neutrofile numar absolut
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de neutrofile' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar neutrofile' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de neutrofile (NEUT)' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'NEUT' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR' ON CONFLICT (alias) DO NOTHING;

-- Neutrofile procent
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Procentul de neutrofile' FROM analiza_standard WHERE cod_standard='NEUTROFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Procentul de neutrofile (NEUT%)' FROM analiza_standard WHERE cod_standard='NEUTROFILE_PCT' ON CONFLICT (alias) DO NOTHING;

-- Limfocite numar absolut
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de limfocite' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar limfocite' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de limfocite (LYM)' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LYM' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR' ON CONFLICT (alias) DO NOTHING;

-- Limfocite procent
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Procentul de limfocite' FROM analiza_standard WHERE cod_standard='LIMFOCITE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Procentul de limfocite (LYM%)' FROM analiza_standard WHERE cod_standard='LIMFOCITE_PCT' ON CONFLICT (alias) DO NOTHING;

-- Monocite numar absolut
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de monocite' FROM analiza_standard WHERE cod_standard='MONOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar monocite' FROM analiza_standard WHERE cod_standard='MONOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de monocite (MON)' FROM analiza_standard WHERE cod_standard='MONOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MON' FROM analiza_standard WHERE cod_standard='MONOCITE_NR' ON CONFLICT (alias) DO NOTHING;

-- Monocite procent
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Procentul de monocite' FROM analiza_standard WHERE cod_standard='MONOCITE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Procentul de monocite (MON%)' FROM analiza_standard WHERE cod_standard='MONOCITE_PCT' ON CONFLICT (alias) DO NOTHING;

-- Eozinofile numar absolut
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de eozinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar eozinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de eozinofile (EOS)' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'EOS' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR' ON CONFLICT (alias) DO NOTHING;

-- Eozinofile procent
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Procentul de eozinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Procentul de eozinofile (EOS%)' FROM analiza_standard WHERE cod_standard='EOZINOFILE_PCT' ON CONFLICT (alias) DO NOTHING;

-- Bazofile numar absolut
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de bazofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar bazofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de bazofile (BAS)' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'BAS' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR' ON CONFLICT (alias) DO NOTHING;

-- Bazofile procent
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Procentul de bazofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Procentul de bazofile (BAS%)' FROM analiza_standard WHERE cod_standard='BAZOFILE_PCT' ON CONFLICT (alias) DO NOTHING;

-- Trombocite
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de trombocite' FROM analiza_standard WHERE cod_standard='PLT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar trombocite' FROM analiza_standard WHERE cod_standard='PLT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar de trombocite (PLT)' FROM analiza_standard WHERE cod_standard='PLT' ON CONFLICT (alias) DO NOTHING;

-- MPV
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Volumul mediu plachetar' FROM analiza_standard WHERE cod_standard='MPV' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Volumul mediu plachetar (MPV)' FROM analiza_standard WHERE cod_standard='MPV' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Volum mediu plachetar' FROM analiza_standard WHERE cod_standard='MPV' ON CONFLICT (alias) DO NOTHING;

-- PDW
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Distributia plachetelor' FROM analiza_standard WHERE cod_standard='PDW' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Distributia plachetelor (PDW-SD)' FROM analiza_standard WHERE cod_standard='PDW' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Distributia plachetelor(trombocitelor) (PDW-SD)' FROM analiza_standard WHERE cod_standard='PDW' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PDW-SD' FROM analiza_standard WHERE cod_standard='PDW' ON CONFLICT (alias) DO NOTHING;

-- VSH
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'VSH (VITEZA DE SEDIMENTARE A HEMATIILOR)' FROM analiza_standard WHERE cod_standard='VSH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Viteza de sedimentare a hematiilor' FROM analiza_standard WHERE cod_standard='VSH' ON CONFLICT (alias) DO NOTHING;

-- ─── Alias-uri pentru analize frecvent nerecunoscute ─────────────────────────

-- ALT (ALAT/TGP)
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALANINAMINOTRANSFERAZA' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alanin aminotransferaza (ALT)' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;

-- AST (ASAT/TGO)
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ASPARTATAMINOTRANSFERAZA' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Aspartat aminotransferaza (AST)' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;

-- Factor reumatoid
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Factor reumatoid' FROM analiza_standard WHERE cod_standard='FR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FACTOR REUMATOID' FROM analiza_standard WHERE cod_standard='FR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RF' FROM analiza_standard WHERE cod_standard='FR' ON CONFLICT (alias) DO NOTHING;

-- IgE
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'IgE' FROM analiza_standard WHERE cod_standard='IGE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'IgE totala' FROM analiza_standard WHERE cod_standard='IGE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'IgE (IMUNOGLOBULINA E)' FROM analiza_standard WHERE cod_standard='IGE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'IGE_TOTAL' FROM analiza_standard WHERE cod_standard='IGE' ON CONFLICT (alias) DO NOTHING;

-- ASLO
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ASLO' FROM analiza_standard WHERE cod_standard='ASLO' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'AntiStreptolizina O' FROM analiza_standard WHERE cod_standard='ASLO' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ANTICORPI ANTI-STREPTOLIZINA O' FROM analiza_standard WHERE cod_standard='ASLO' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Anticorpi anti-streptolizina O (ASLO)' FROM analiza_standard WHERE cod_standard='ASLO' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Anti-streptolisin O' FROM analiza_standard WHERE cod_standard='ASLO' ON CONFLICT (alias) DO NOTHING;

-- Anti-TPO (corectare alias gresit cu ASLO)
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ANTICORPI ANTI-TPO' FROM analiza_standard WHERE cod_standard='ANTI_TPO' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ATPO' FROM analiza_standard WHERE cod_standard='ANTI_TPO' ON CONFLICT (alias) DO NOTHING;

-- PTH
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'iPTH' FROM analiza_standard WHERE cod_standard='PTH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PTH' FROM analiza_standard WHERE cod_standard='PTH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Parathormon' FROM analiza_standard WHERE cod_standard='PTH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'iPTH (PARATHORMON INTACT)' FROM analiza_standard WHERE cod_standard='PTH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Parathormon intact' FROM analiza_standard WHERE cod_standard='PTH' ON CONFLICT (alias) DO NOTHING;

-- DAO
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'DAO' FROM analiza_standard WHERE cod_standard='DAO' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Diaminoxidaza' FROM analiza_standard WHERE cod_standard='DAO' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'DIAMINOXIDAZA (DAO)' FROM analiza_standard WHERE cod_standard='DAO' ON CONFLICT (alias) DO NOTHING;

-- Homocisteina
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Homocisteina' FROM analiza_standard WHERE cod_standard='HOMOCIST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Homocisteinemia' FROM analiza_standard WHERE cod_standard='HOMOCIST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Homocysteine' FROM analiza_standard WHERE cod_standard='HOMOCIST' ON CONFLICT (alias) DO NOTHING;

-- Complement
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'COMPLEMENT C3' FROM analiza_standard WHERE cod_standard='COMPLEMENT_C3' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'C3' FROM analiza_standard WHERE cod_standard='COMPLEMENT_C3' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'COMPLEMENT C4' FROM analiza_standard WHERE cod_standard='COMPLEMENT_C4' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'C4' FROM analiza_standard WHERE cod_standard='COMPLEMENT_C4' ON CONFLICT (alias) DO NOTHING;

-- Calciu ionic
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Calciu ionic' FROM analiza_standard WHERE cod_standard='CALCIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CALCIU IONIC' FROM analiza_standard WHERE cod_standard='CALCIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CALCIU SERIC' FROM analiza_standard WHERE cod_standard='CALCIU' ON CONFLICT (alias) DO NOTHING;

-- Fier seric
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FIER SERIC (SIDEREMIE)' FROM analiza_standard WHERE cod_standard='FIER' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fier seric (Sideremie)' FROM analiza_standard WHERE cod_standard='FIER' ON CONFLICT (alias) DO NOTHING;

-- Magneziu
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MAGNEZIU SERIC' FROM analiza_standard WHERE cod_standard='MAGNEZIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Magneziu seric' FROM analiza_standard WHERE cod_standard='MAGNEZIU' ON CONFLICT (alias) DO NOTHING;

-- Potasiu
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'POTASIU SERIC' FROM analiza_standard WHERE cod_standard='POTASIU' ON CONFLICT (alias) DO NOTHING;

-- Vitamina B12 (alias explicit pentru a evita confuzia cu VIT_D)
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'VITAMINA B12' FROM analiza_standard WHERE cod_standard='VIT_B12' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamina B 12' FROM analiza_standard WHERE cod_standard='VIT_B12' ON CONFLICT (alias) DO NOTHING;

-- Vitamina D
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '25-OH-VITAMINA D' FROM analiza_standard WHERE cod_standard='VIT_D' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '25-OH Vitamina D3' FROM analiza_standard WHERE cod_standard='VIT_D' ON CONFLICT (alias) DO NOTHING;

-- Acid folic
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FOLATI SERICI' FROM analiza_standard WHERE cod_standard='ACID_FOLIC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Folati serici (Acid folic)' FROM analiza_standard WHERE cod_standard='ACID_FOLIC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FOLATI SERICI (ACID FOLIC)' FROM analiza_standard WHERE cod_standard='ACID_FOLIC' ON CONFLICT (alias) DO NOTHING;

-- Glucoza
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'GLUCOZA SERICA (GLICEMIE)' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoza serica (Glicemie)' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;

-- Creatinina
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina serica' FROM analiza_standard WHERE cod_standard='CREATININA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CREATININA SERICA' FROM analiza_standard WHERE cod_standard='CREATININA' ON CONFLICT (alias) DO NOTHING;

-- eGFR
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'eGFR' FROM analiza_standard WHERE cod_standard='EGFR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RFG estimat' FROM analiza_standard WHERE cod_standard='EGFR' ON CONFLICT (alias) DO NOTHING;

-- CRP
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PROTEINA C REACTIVA (CRP)' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteina C reactiva (CRP)' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;

-- FT3
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FT3 (TRIIODOTIRONINA LIBERA)' FROM analiza_standard WHERE cod_standard='FT3' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Triiodotironina libera' FROM analiza_standard WHERE cod_standard='FT3' ON CONFLICT (alias) DO NOTHING;

-- FT4
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FT4 (TIROXINA LIBERA)' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Tiroxina libera (FT4)' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;

-- TSH
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TSH (HORMON DE STIMULARE TIROIDIANA)' FROM analiza_standard WHERE cod_standard='TSH' ON CONFLICT (alias) DO NOTHING;

-- Colesterol
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'COLESTEROL TOTAL' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HDL COLESTEROL' FROM analiza_standard WHERE cod_standard='HDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL COLESTEROL' FROM analiza_standard WHERE cod_standard='LDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TRIGLICERIDE SERICE' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE' ON CONFLICT (alias) DO NOTHING;
