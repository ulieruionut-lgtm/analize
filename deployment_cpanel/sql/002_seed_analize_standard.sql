-- Date inițiale: analize standard + alias-uri (exemple)
-- Rulează după 001_schema.sql

INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('GLUCOZA_FASTING', 'Glicemie'),
('HB', 'Hemoglobină'),
('WBC', 'Leucocite'),
('RBC', 'Eritrocite'),
('PLT', 'Trombocite'),
('HBA1C', 'Hemoglobină glicată'),
('CREATININA', 'Creatinină'),
('ALT', 'ALAT'),
('AST', 'ASAT'),
('COLESTEROL_TOTAL', 'Colesterol total'),
('HDL', 'HDL colesterol'),
('LDL', 'LDL colesterol'),
('TSH', 'TSH')
ON CONFLICT (cod_standard) DO NOTHING;

-- Alias-uri (exemple; extinde după nevoie)
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['Glicemie', 'Glucose', 'Glucoză', 'Glucoză serică', 'GLU', 'Glicemie la nemâncat'])
FROM analiza_standard WHERE cod_standard = 'GLUCOZA_FASTING'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['Hemoglobină', 'Hb', 'HGB', 'Hemoglobina'])
FROM analiza_standard WHERE cod_standard = 'HB'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['Leucocite', 'WBC', 'Globule albe', 'LEU'])
FROM analiza_standard WHERE cod_standard = 'WBC'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['Eritrocite', 'RBC', 'Globule roșii'])
FROM analiza_standard WHERE cod_standard = 'RBC'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['Trombocite', 'PLT', 'Plaquettes', 'Trombocite'])
FROM analiza_standard WHERE cod_standard = 'PLT'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['Hemoglobină glicată', 'HbA1c', 'HBA1C', 'Glycated hemoglobin'])
FROM analiza_standard WHERE cod_standard = 'HBA1C'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['Creatinină', 'Creatinine', 'CREAT', 'Creatinină serică'])
FROM analiza_standard WHERE cod_standard = 'CREATININA'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['ALAT', 'ALT', 'GPT', 'Transaminaze ALT', 'TGP (ALAT)', 'TGP'])
FROM analiza_standard WHERE cod_standard = 'ALT'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['ASAT', 'AST', 'GOT', 'Transaminaze AST', 'TGO (ASAT)', 'TGO'])
FROM analiza_standard WHERE cod_standard = 'AST'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['Colesterol total', 'Cholesterol total', 'CHOL'])
FROM analiza_standard WHERE cod_standard = 'COLESTEROL_TOTAL'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['HDL', 'HDL colesterol', 'HDL-C'])
FROM analiza_standard WHERE cod_standard = 'HDL'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['LDL', 'LDL colesterol', 'LDL-C'])
FROM analiza_standard WHERE cod_standard = 'LDL'
ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, unnest(ARRAY['TSH', 'Hormon stimulant tiroidian', 'TSH (hormon hipofizar tireostimulator bazal)'])
FROM analiza_standard WHERE cod_standard = 'TSH'
ON CONFLICT (alias) DO NOTHING;

-- Alias-uri Bioclinica (denumiri lungi) – Fier/Feritină/FT4 rămân cu denumire_raw dacă nu adaugi analize_standard
