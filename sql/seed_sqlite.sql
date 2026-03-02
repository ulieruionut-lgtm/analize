-- Seed analize standard + alias (SQLite)

INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
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
('TSH', 'TSH');

INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Glicemie' FROM analiza_standard WHERE cod_standard = 'GLUCOZA_FASTING' UNION SELECT id, 'Glucose' FROM analiza_standard WHERE cod_standard = 'GLUCOZA_FASTING' UNION SELECT id, 'Glucoză' FROM analiza_standard WHERE cod_standard = 'GLUCOZA_FASTING' UNION SELECT id, 'Glucoză serică' FROM analiza_standard WHERE cod_standard = 'GLUCOZA_FASTING' UNION SELECT id, 'GLU' FROM analiza_standard WHERE cod_standard = 'GLUCOZA_FASTING' UNION SELECT id, 'Glicemie la nemâncat' FROM analiza_standard WHERE cod_standard = 'GLUCOZA_FASTING';

INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobină' FROM analiza_standard WHERE cod_standard = 'HB';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hb' FROM analiza_standard WHERE cod_standard = 'HB';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HGB' FROM analiza_standard WHERE cod_standard = 'HB';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina' FROM analiza_standard WHERE cod_standard = 'HB';

INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Leucocite' FROM analiza_standard WHERE cod_standard = 'WBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'WBC' FROM analiza_standard WHERE cod_standard = 'WBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Globule albe' FROM analiza_standard WHERE cod_standard = 'WBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LEU' FROM analiza_standard WHERE cod_standard = 'WBC';

INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eritrocite' FROM analiza_standard WHERE cod_standard = 'RBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RBC' FROM analiza_standard WHERE cod_standard = 'RBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Globule roșii' FROM analiza_standard WHERE cod_standard = 'RBC';

INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Trombocite' FROM analiza_standard WHERE cod_standard = 'PLT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PLT' FROM analiza_standard WHERE cod_standard = 'PLT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Plaquettes' FROM analiza_standard WHERE cod_standard = 'PLT';

INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobină glicată' FROM analiza_standard WHERE cod_standard = 'HBA1C';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HbA1c' FROM analiza_standard WHERE cod_standard = 'HBA1C';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HBA1C' FROM analiza_standard WHERE cod_standard = 'HBA1C';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glycated hemoglobin' FROM analiza_standard WHERE cod_standard = 'HBA1C';

INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinină' FROM analiza_standard WHERE cod_standard = 'CREATININA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinine' FROM analiza_standard WHERE cod_standard = 'CREATININA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CREAT' FROM analiza_standard WHERE cod_standard = 'CREATININA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinină serică' FROM analiza_standard WHERE cod_standard = 'CREATININA';

INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALAT' FROM analiza_standard WHERE cod_standard = 'ALT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALT' FROM analiza_standard WHERE cod_standard = 'ALT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGP (ALAT)' FROM analiza_standard WHERE cod_standard = 'ALT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGP' FROM analiza_standard WHERE cod_standard = 'ALT';

INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ASAT' FROM analiza_standard WHERE cod_standard = 'AST';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'AST' FROM analiza_standard WHERE cod_standard = 'AST';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGO (ASAT)' FROM analiza_standard WHERE cod_standard = 'AST';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGO' FROM analiza_standard WHERE cod_standard = 'AST';

INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol total' FROM analiza_standard WHERE cod_standard = 'COLESTEROL_TOTAL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cholesterol total' FROM analiza_standard WHERE cod_standard = 'COLESTEROL_TOTAL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HDL' FROM analiza_standard WHERE cod_standard = 'HDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HDL colesterol' FROM analiza_standard WHERE cod_standard = 'HDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL' FROM analiza_standard WHERE cod_standard = 'LDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL colesterol' FROM analiza_standard WHERE cod_standard = 'LDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TSH' FROM analiza_standard WHERE cod_standard = 'TSH';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TSH (hormon hipofizar tireostimulator bazal)' FROM analiza_standard WHERE cod_standard = 'TSH';
