-- Migrare 019: Aliasuri MedLife PDR Brasov + Calciu ionic + fix TGO/TGP cu slash
-- Testat pe buletinul Pivets Nicole (MedLife PDR, 02.03.2026)
-- Actualizat cu buletinul Tutungiu Gabriela (MedLife PDR, 02.10.2025)

-- TGO/AST (format MedLife PDR cu slash)
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'TGO/AST' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'TGO / AST' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;

-- TGP/ALT (format MedLife PDR cu slash)
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'TGP/ALT' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'TGP / ALT' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;

-- ASLO cantitativ (MedLife PDR)
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'ASLO cantitativ' FROM analiza_standard WHERE cod_standard='ASLO' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'ASLO Cantitativ' FROM analiza_standard WHERE cod_standard='ASLO' ON CONFLICT (alias) DO NOTHING;

-- Calciu seric total (MedLife PDR)
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Calciu seric total' FROM analiza_standard WHERE cod_standard='CALCIU' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Ca seric total' FROM analiza_standard WHERE cod_standard='CALCIU' ON CONFLICT (alias) DO NOTHING;

-- Calciu ionic (analiza noua daca nu exista)
INSERT INTO analiza_standard (cod_standard, denumire, categorie, unitate)
VALUES ('CALCIU_IONIC', 'Calciu ionic', 'Biochimie', 'mg/dl')
ON CONFLICT (cod_standard) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Calciu ionic' FROM analiza_standard WHERE cod_standard='CALCIU_IONIC' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Ca ionic' FROM analiza_standard WHERE cod_standard='CALCIU_IONIC' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Calciu ionizat' FROM analiza_standard WHERE cod_standard='CALCIU_IONIC' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Calciu ionizat (Ca++)' FROM analiza_standard WHERE cod_standard='CALCIU_IONIC' ON CONFLICT (alias) DO NOTHING;

-- Free T4 (variante MedLife)
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Free T4' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'fT4' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;

-- Feritina variante MedLife PDR
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Feritina' FROM analiza_standard WHERE cod_standard='FERITINA' ON CONFLICT (alias) DO NOTHING;

-- Sideremie (fier seric)
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Sideremie' FROM analiza_standard WHERE cod_standard='FIER' ON CONFLICT (alias) DO NOTHING;

-- Fosfataza alcalina variante MedLife
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Fosfataza alcalina' FROM analiza_standard WHERE cod_standard='ALP' ON CONFLICT (alias) DO NOTHING;

-- VEM / MCH / CHEM variante scurte MedLife PDR (deja in 004 dar adaugam ON CONFLICT safe)
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'VEM' FROM analiza_standard WHERE cod_standard='MCV' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'MCH' FROM analiza_standard WHERE cod_standard='MCH' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'CHEM' FROM analiza_standard WHERE cod_standard='MCHC' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'VTM' FROM analiza_standard WHERE cod_standard='MPV' ON CONFLICT (alias) DO NOTHING;

-- VIM: OCR MedLife PDR confunda VTM cu VIM (litera T → I)
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'VIM' FROM analiza_standard WHERE cod_standard='MPV' ON CONFLICT (alias) DO NOTHING;

-- HDL Colesterol (MedLife PDR: C mare, cu si fara liniuta)
-- Existent: 'HDL colesterol' (c mic) — lipseste varianta cu C mare
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'HDL Colesterol' FROM analiza_standard WHERE cod_standard='HDL' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'HDL-Colesterol' FROM analiza_standard WHERE cod_standard='HDL' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'HDL- Colesterol' FROM analiza_standard WHERE cod_standard='HDL' ON CONFLICT (alias) DO NOTHING;

-- LDL-Colesterol (MedLife PDR: C mare)
-- Existent: 'LDL-colesterol' (c mic) — lipseste varianta cu C mare
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'LDL-Colesterol' FROM analiza_standard WHERE cod_standard='LDL' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'LDL Colesterol' FROM analiza_standard WHERE cod_standard='LDL' ON CONFLICT (alias) DO NOTHING;

-- Folat seric (MedLife PDR — existent 'Folat' dar nu 'Folat seric')
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Folat seric' FROM analiza_standard WHERE cod_standard='ACID_FOLIC' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Folat Seric' FROM analiza_standard WHERE cod_standard='ACID_FOLIC' ON CONFLICT (alias) DO NOTHING;

-- Vitamina B12 (variante cu spatiu diferit sau majuscule)
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Vitamina B12' FROM analiza_standard WHERE cod_standard='VIT_B12' ON CONFLICT (alias) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'VITAMINA B12' FROM analiza_standard WHERE cod_standard='VIT_B12' ON CONFLICT (alias) DO NOTHING;

-- Colesterol total (variante MedLife PDR)
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Colesterol total' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL' ON CONFLICT (alias) DO NOTHING;

-- Trigliceride (variante MedLife PDR — singular fara 'serice')
INSERT INTO analiza_alias (analiza_standard_id, alias)
SELECT id, 'Trigliceride' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE' ON CONFLICT (alias) DO NOTHING;
