-- Migrare 004: analize standard extinse + alias-uri (PostgreSQL)
-- Laboratoare acoperite: Bioclinica, MedLife, Synevo, Medicover, Regina Maria
-- Foloseste INSERT ... ON CONFLICT DO NOTHING pentru a nu duplica date existente.

-- ─── Tabel analize necunoscute (auto-invatare) ──────────────────────────────
CREATE TABLE IF NOT EXISTS analiza_necunoscuta (
    id SERIAL PRIMARY KEY,
    denumire_raw TEXT NOT NULL UNIQUE,
    aparitii INTEGER NOT NULL DEFAULT 1,
    aprobata INTEGER NOT NULL DEFAULT 0,       -- 0=neaprobata, 1=aprobata si mapata
    analiza_standard_id INTEGER REFERENCES analiza_standard(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_necunoscute_raw ON analiza_necunoscuta(denumire_raw);

-- ─── Analize standard (extinse) ──────────────────────────────────────────────

-- Hemoleucograma
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('WBC',       'Leucocite (WBC)'),
('RBC',       'Eritrocite (RBC)'),
('HB',        'Hemoglobină'),
('HCT',       'Hematocrit'),
('MCV',       'VEM – Volum eritrocitar mediu'),
('MCH',       'HEM – Hemoglobina eritrocitara medie'),
('MCHC',      'CHEM – Concentratia Hb eritrocitare medii'),
('RDW',       'RDW – Indice distributie eritrocite'),
('PLT',       'Trombocite (PLT)'),
('MPV',       'VTM – Volum trombocitar mediu'),
('PDW',       'PDW – Indice distributie trombocite'),
('PCT',       'PCT – Trombocrit'),
('NEUTROFILE_PCT',  'Neutrofile (%)'),
('NEUTROFILE_NR',   'Neutrofile (numar absolut)'),
('LIMFOCITE_PCT',   'Limfocite (%)'),
('LIMFOCITE_NR',    'Limfocite (numar absolut)'),
('MONOCITE_PCT',    'Monocite (%)'),
('MONOCITE_NR',     'Monocite (numar absolut)'),
('EOZINOFILE_PCT',  'Eozinofile (%)'),
('EOZINOFILE_NR',   'Eozinofile (numar absolut)'),
('BAZOFILE_PCT',    'Bazofile (%)'),
('BAZOFILE_NR',     'Bazofile (numar absolut)') ON CONFLICT (cod_standard) DO NOTHING;

-- Biochimie generala
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('GLUCOZA_FASTING', 'Glicemie'),
('UREE',            'Uree serica'),
('CREATININA',      'Creatinina serica'),
('ACID_URIC',       'Acid uric'),
('PROTEINE_TOT',    'Proteine totale serice'),
('ALBUMINA',        'Albumina serica'),
('GLOBULINE',       'Globuline'),
('RAPORT_AG',       'Raport albumina/globuline'),
('BILIRUBIN_TOT',   'Bilirubina totala'),
('BILIRUBIN_DIR',   'Bilirubina directa (conjugata)'),
('BILIRUBIN_IND',   'Bilirubina indirecta'),
('AMILAZA',         'Amilaza serica'),
('LIPAZA',          'Lipaza serica'),
('LDH',             'LDH – Lactat dehidrogenaza'),
('EGFR',            'RFG estimat (eGFR)') ON CONFLICT (cod_standard) DO NOTHING;

-- Enzime hepatice
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('ALT',    'ALAT (TGP)'),
('AST',    'ASAT (TGO)'),
('GGT',    'GGT – Gama glutamil transferaza'),
('ALP',    'Fosfataza alcalina'),
('HBA1C',  'Hemoglobina glicata (HbA1c)') ON CONFLICT (cod_standard) DO NOTHING;

-- Lipide
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('COLESTEROL_TOTAL', 'Colesterol total'),
('HDL',              'HDL colesterol'),
('LDL',              'LDL colesterol'),
('TRIGLICERIDE',     'Trigliceride'),
('NON_HDL',          'Non-HDL colesterol'),
('LPDL',             'Lp(a) – Lipoproteina a') ON CONFLICT (cod_standard) DO NOTHING;

-- Electrolyti & minerale
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('SODIU',    'Sodiu seric (Na)'),
('POTASIU',  'Potasiu seric (K)'),
('CALCIU',   'Calciu seric (Ca)'),
('MAGNEZIU', 'Magneziu seric'),
('FOSFOR',   'Fosfor seric'),
('CLOR',     'Clor seric (Cl)'),
('FIER',     'Fier seric'),
('FERITINA', 'Feritina'),
('TRANSFERINA', 'Transferina'),
('TIBC',     'TIBC – Capacitate totala de legare a fierului'),
('VIT_D',    'Vitamina D (25-OH)'),
('VIT_B12',  'Vitamina B12 (Cobalamina)'),
('ACID_FOLIC','Acid folic (Vitamina B9)'),
('VIT_B1',   'Vitamina B1 (Tiamina)'),
('ZINC',     'Zinc seric') ON CONFLICT (cod_standard) DO NOTHING;

-- Hormoni tiroidieni
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('TSH',      'TSH'),
('FT4',      'T4 liber (FT4)'),
('FT3',      'T3 liber (FT3)'),
('T4',       'T4 total'),
('T3',       'T3 total'),
('ANTI_TPO', 'Anticorpi anti-TPO'),
('ANTI_TG',  'Anticorpi anti-tiroglobulina'),
('TG',       'Tiroglobulina') ON CONFLICT (cod_standard) DO NOTHING;

-- Hormoni sexuali si suprarenali
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('CORTIZOL',    'Cortizol'),
('INSULINA',    'Insulina bazala'),
('HOMA_IR',     'HOMA-IR'),
('FSH',         'FSH'),
('LH',          'LH'),
('ESTRADIOL',   'Estradiol (E2)'),
('PROGESTERON', 'Progesteron'),
('TESTOSTERON', 'Testosteron total'),
('TESTOST_L',   'Testosteron liber'),
('DHEA_S',      'DHEA-S'),
('PROLACTINA',  'Prolactina'),
('AMH',         'AMH – Hormon anti-Mullerian'),
('PSA_TOTAL',   'PSA total'),
('PSA_LIBER',   'PSA liber'),
('BETA_HCG',    'Beta-hCG') ON CONFLICT (cod_standard) DO NOTHING;

-- Inflamatie si imunologie
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('CRP',          'CRP – Proteina C reactiva'),
('CRP_HS',       'CRP ultrasensibil (hs-CRP)'),
('VSH',          'VSH – Viteza de sedimentare a hematiilor'),
('FIBRINOGEN',   'Fibrinogen'),
('IL6',          'Interleukina 6 (IL-6)'),
('IGA',          'Imunoglobulina A (IgA)'),
('IGG',          'Imunoglobulina G (IgG)'),
('IGM',          'Imunoglobulina M (IgM)'),
('IGE_TOTAL',    'IgE totala'),
('COMPLEMENT_C3','Complement C3'),
('COMPLEMENT_C4','Complement C4'),
('ANA',          'Anticorpi antinucleari (ANA)'),
('ANTI_DS_DNA',  'Anticorpi anti-dsDNA'),
('FR',           'Factor reumatoid (FR)'),
('ANCA',         'ANCA'),
('ANTI_CCP',     'Anticorpi anti-CCP') ON CONFLICT (cod_standard) DO NOTHING;

-- Coagulare
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('PT',           'Timp de protrombina (PT)'),
('INR',          'INR'),
('APTT',         'aPTT – Timp partial de tromboplastina activata'),
('TT',           'Timp de trombina'),
('D_DIMERI',     'D-dimeri') ON CONFLICT (cod_standard) DO NOTHING;

-- Markeri tumorali
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('CEA',          'CEA – Antigen carcino-embrionar'),
('CA_125',       'CA 125'),
('CA_19_9',      'CA 19-9'),
('CA_15_3',      'CA 15-3'),
('AFP',          'Alfa-fetoproteina (AFP)'),
('CA_72_4',      'CA 72-4') ON CONFLICT (cod_standard) DO NOTHING;

-- Serologie infectioasa
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('HBSAG',        'AgHBs – Antigen hepatita B'),
('ANTI_HBS',     'Ac anti-HBs'),
('ANTI_HCV',     'Ac anti-HCV'),
('ANTI_HIV',     'Ac anti-HIV 1+2'),
('VDRL',         'VDRL / Sifilis'),
('TOXOPLASMA_IGA','Toxoplasma IgA'),
('TOXOPLASMA_IGG','Toxoplasma IgG'),
('TOXOPLASMA_IGM','Toxoplasma IgM'),
('CMV_IGG',      'CMV IgG'),
('CMV_IGM',      'CMV IgM'),
('EBV_IGG',      'EBV – VCA IgG'),
('EBV_IGM',      'EBV – VCA IgM'),
('RUBELLA_IGG',  'Rubeola IgG'),
('RUBELLA_IGM',  'Rubeola IgM') ON CONFLICT (cod_standard) DO NOTHING;

-- Urina
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('URINA_SUMAR',   'Sumar urina (examen complet)'),
('MICROALBUMIN',  'Microalbuminurie'),
('CREAT_URINA',   'Creatinina urinara'),
('CRISTALE_URINA','Cristale urina'),
('FLORA_URINA',   'Flora microbiana urina') ON CONFLICT (cod_standard) DO NOTHING;

-- Alias Regina Maria / Vladasel (format sediment urinar)
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Flora microbiana' FROM analiza_standard WHERE cod_standard='FLORA_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '1.2.12 Flora microbiana' FROM analiza_standard WHERE cod_standard='FLORA_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alte' FROM analiza_standard WHERE cod_standard='CRISTALE_URINA' ON CONFLICT (alias) DO NOTHING;

-- ─── ALIAS-URI ────────────────────────────────────────────────────────────────
-- Format: INSERT INTO analiza_alias (analiza_standard_id, alias)
--         SELECT id, 'alias' FROM analiza_standard WHERE cod_standard = 'COD';

-- ── Leucocite ──────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Leucocite' FROM analiza_standard WHERE cod_standard='WBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'WBC' FROM analiza_standard WHERE cod_standard='WBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. leucocite' FROM analiza_standard WHERE cod_standard='WBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar leucocite' FROM analiza_standard WHERE cod_standard='WBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Globule albe' FROM analiza_standard WHERE cod_standard='WBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LEU' FROM analiza_standard WHERE cod_standard='WBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'White Blood Cells' FROM analiza_standard WHERE cod_standard='WBC' ON CONFLICT (alias) DO NOTHING;

-- ── Eritrocite ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eritrocite' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RBC' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. eritrocite' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar eritrocite' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Globule rosii' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Red Blood Cells' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;

-- ── Hemoglobina ────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina' FROM analiza_standard WHERE cod_standard='HB' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobină' FROM analiza_standard WHERE cod_standard='HB' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HGB' FROM analiza_standard WHERE cod_standard='HB' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hb' FROM analiza_standard WHERE cod_standard='HB' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Haemoglobin' FROM analiza_standard WHERE cod_standard='HB' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobin' FROM analiza_standard WHERE cod_standard='HB' ON CONFLICT (alias) DO NOTHING;

-- ── Hematocrit ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hematocrit' FROM analiza_standard WHERE cod_standard='HCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HCT' FROM analiza_standard WHERE cod_standard='HCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ht' FROM analiza_standard WHERE cod_standard='HCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Haematocrit' FROM analiza_standard WHERE cod_standard='HCT' ON CONFLICT (alias) DO NOTHING;

-- ── MCV / VEM ──────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'VEM' FROM analiza_standard WHERE cod_standard='MCV' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MCV' FROM analiza_standard WHERE cod_standard='MCV' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Volum eritrocitar mediu' FROM analiza_standard WHERE cod_standard='MCV' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mean Corpuscular Volume' FROM analiza_standard WHERE cod_standard='MCV' ON CONFLICT (alias) DO NOTHING;

-- ── MCH / HEM ──────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MCH' FROM analiza_standard WHERE cod_standard='MCH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HEM' FROM analiza_standard WHERE cod_standard='MCH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina eritrocitara medie' FROM analiza_standard WHERE cod_standard='MCH' ON CONFLICT (alias) DO NOTHING;

-- ── MCHC / CHEM ────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MCHC' FROM analiza_standard WHERE cod_standard='MCHC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CHEM' FROM analiza_standard WHERE cod_standard='MCHC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Concentratia Hb eritrocitare' FROM analiza_standard WHERE cod_standard='MCHC' ON CONFLICT (alias) DO NOTHING;

-- ── RDW ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RDW' FROM analiza_standard WHERE cod_standard='RDW' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RDW-CV' FROM analiza_standard WHERE cod_standard='RDW' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RDW-SD' FROM analiza_standard WHERE cod_standard='RDW' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Indice distributie eritrocite' FROM analiza_standard WHERE cod_standard='RDW' ON CONFLICT (alias) DO NOTHING;

-- ── Trombocite ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Trombocite' FROM analiza_standard WHERE cod_standard='PLT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PLT' FROM analiza_standard WHERE cod_standard='PLT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. trombocite' FROM analiza_standard WHERE cod_standard='PLT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar trombocite' FROM analiza_standard WHERE cod_standard='PLT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Platelets' FROM analiza_standard WHERE cod_standard='PLT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Plaquettes' FROM analiza_standard WHERE cod_standard='PLT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Plachete' FROM analiza_standard WHERE cod_standard='PLT' ON CONFLICT (alias) DO NOTHING;

-- ── MPV / VTM ──────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MPV' FROM analiza_standard WHERE cod_standard='MPV' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'VTM' FROM analiza_standard WHERE cod_standard='MPV' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Volum trombocitar mediu' FROM analiza_standard WHERE cod_standard='MPV' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mean Platelet Volume' FROM analiza_standard WHERE cod_standard='MPV' ON CONFLICT (alias) DO NOTHING;

-- ── PDW ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PDW' FROM analiza_standard WHERE cod_standard='PDW' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Platelet Distribution Width' FROM analiza_standard WHERE cod_standard='PDW' ON CONFLICT (alias) DO NOTHING;

-- ── PCT ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PCT' FROM analiza_standard WHERE cod_standard='PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Trombocrit' FROM analiza_standard WHERE cod_standard='PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Plateletcrit' FROM analiza_standard WHERE cod_standard='PCT' ON CONFLICT (alias) DO NOTHING;

-- ── Neutrofile % ───────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '% Neutrofile' FROM analiza_standard WHERE cod_standard='NEUTROFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Neutrofile %' FROM analiza_standard WHERE cod_standard='NEUTROFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'NEUT%' FROM analiza_standard WHERE cod_standard='NEUTROFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Neutrophils %' FROM analiza_standard WHERE cod_standard='NEUTROFILE_PCT' ON CONFLICT (alias) DO NOTHING;

-- ── Neutrofile absolut ─────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. neutrofile' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Neutrofile' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'NEUT#' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Neutrophils' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR' ON CONFLICT (alias) DO NOTHING;

-- ── Limfocite % ────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '% Limfocite' FROM analiza_standard WHERE cod_standard='LIMFOCITE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Limfocite %' FROM analiza_standard WHERE cod_standard='LIMFOCITE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LYM%' FROM analiza_standard WHERE cod_standard='LIMFOCITE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Lymphocytes %' FROM analiza_standard WHERE cod_standard='LIMFOCITE_PCT' ON CONFLICT (alias) DO NOTHING;

-- ── Limfocite absolut ──────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. limfocite' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Limfocite' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LYM#' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Lymphocytes' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR' ON CONFLICT (alias) DO NOTHING;

-- ── Monocite % ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '% Monocite' FROM analiza_standard WHERE cod_standard='MONOCITE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Monocite %' FROM analiza_standard WHERE cod_standard='MONOCITE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MON%' FROM analiza_standard WHERE cod_standard='MONOCITE_PCT' ON CONFLICT (alias) DO NOTHING;

-- ── Monocite absolut ───────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. monocite' FROM analiza_standard WHERE cod_standard='MONOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Monocite' FROM analiza_standard WHERE cod_standard='MONOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MON#' FROM analiza_standard WHERE cod_standard='MONOCITE_NR' ON CONFLICT (alias) DO NOTHING;

-- ── Eozinofile % ───────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '% Eozinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eozinofile %' FROM analiza_standard WHERE cod_standard='EOZINOFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'EOS%' FROM analiza_standard WHERE cod_standard='EOZINOFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eosinofile %' FROM analiza_standard WHERE cod_standard='EOZINOFILE_PCT' ON CONFLICT (alias) DO NOTHING;

-- ── Eozinofile absolut ─────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. eozinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eozinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'EOS#' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eosinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR' ON CONFLICT (alias) DO NOTHING;

-- ── Bazofile % ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '% Basofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bazofile %' FROM analiza_standard WHERE cod_standard='BAZOFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Basofile %' FROM analiza_standard WHERE cod_standard='BAZOFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'BAS%' FROM analiza_standard WHERE cod_standard='BAZOFILE_PCT' ON CONFLICT (alias) DO NOTHING;

-- ── Bazofile absolut ───────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. basofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. bazofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bazofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Basofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'BAS#' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR' ON CONFLICT (alias) DO NOTHING;

-- ── Glicemie ───────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glicemie' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoza' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoză' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucose' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'GLU' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoza serica' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoza serică' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glicemie a jeun' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glicemie la nemâncat' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;

-- ── Uree ───────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Uree' FROM analiza_standard WHERE cod_standard='UREE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Uree serica' FROM analiza_standard WHERE cod_standard='UREE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Uree serică' FROM analiza_standard WHERE cod_standard='UREE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Urea' FROM analiza_standard WHERE cod_standard='UREE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'BUN' FROM analiza_standard WHERE cod_standard='UREE' ON CONFLICT (alias) DO NOTHING;

-- ── Creatinina ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina' FROM analiza_standard WHERE cod_standard='CREATININA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinină' FROM analiza_standard WHERE cod_standard='CREATININA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinine' FROM analiza_standard WHERE cod_standard='CREATININA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CREAT' FROM analiza_standard WHERE cod_standard='CREATININA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina serica' FROM analiza_standard WHERE cod_standard='CREATININA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina serică' FROM analiza_standard WHERE cod_standard='CREATININA' ON CONFLICT (alias) DO NOTHING;

-- ── Acid uric ──────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Acid uric' FROM analiza_standard WHERE cod_standard='ACID_URIC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Uric acid' FROM analiza_standard WHERE cod_standard='ACID_URIC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'AU' FROM analiza_standard WHERE cod_standard='ACID_URIC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Guta - acid uric' FROM analiza_standard WHERE cod_standard='ACID_URIC' ON CONFLICT (alias) DO NOTHING;

-- ── Proteine totale ────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteine totale' FROM analiza_standard WHERE cod_standard='PROTEINE_TOT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteine totale serice' FROM analiza_standard WHERE cod_standard='PROTEINE_TOT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Total Protein' FROM analiza_standard WHERE cod_standard='PROTEINE_TOT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TP' FROM analiza_standard WHERE cod_standard='PROTEINE_TOT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteine' FROM analiza_standard WHERE cod_standard='PROTEINE_TOT' ON CONFLICT (alias) DO NOTHING;

-- ── Albumina ───────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumina' FROM analiza_standard WHERE cod_standard='ALBUMINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumină' FROM analiza_standard WHERE cod_standard='ALBUMINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumin' FROM analiza_standard WHERE cod_standard='ALBUMINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALB' FROM analiza_standard WHERE cod_standard='ALBUMINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumina serica' FROM analiza_standard WHERE cod_standard='ALBUMINA' ON CONFLICT (alias) DO NOTHING;

-- ── Bilirubina ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina totala' FROM analiza_standard WHERE cod_standard='BILIRUBIN_TOT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina totală' FROM analiza_standard WHERE cod_standard='BILIRUBIN_TOT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubin total' FROM analiza_standard WHERE cod_standard='BILIRUBIN_TOT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'BIL-T' FROM analiza_standard WHERE cod_standard='BILIRUBIN_TOT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TBIL' FROM analiza_standard WHERE cod_standard='BILIRUBIN_TOT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina directa' FROM analiza_standard WHERE cod_standard='BILIRUBIN_DIR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina directă' FROM analiza_standard WHERE cod_standard='BILIRUBIN_DIR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubin direct' FROM analiza_standard WHERE cod_standard='BILIRUBIN_DIR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'DBIL' FROM analiza_standard WHERE cod_standard='BILIRUBIN_DIR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'BIL-D' FROM analiza_standard WHERE cod_standard='BILIRUBIN_DIR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina indirecta' FROM analiza_standard WHERE cod_standard='BILIRUBIN_IND' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina indirectă' FROM analiza_standard WHERE cod_standard='BILIRUBIN_IND' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'IBIL' FROM analiza_standard WHERE cod_standard='BILIRUBIN_IND' ON CONFLICT (alias) DO NOTHING;

-- ── ALAT / TGP ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALAT' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALT' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGP' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGP (ALAT)' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALT (ALAT)' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alanin aminotransferaza' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alanine Aminotransferase' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'GPT' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;

-- ── ASAT / TGO ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ASAT' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'AST' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGO' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGO (ASAT)' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'AST (ASAT)' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Aspartat aminotransferaza' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Aspartate Aminotransferase' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'GOT' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;

-- ── GGT ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'GGT' FROM analiza_standard WHERE cod_standard='GGT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gama GT' FROM analiza_standard WHERE cod_standard='GGT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gamma GT' FROM analiza_standard WHERE cod_standard='GGT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gamma-GT' FROM analiza_standard WHERE cod_standard='GGT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'GGT (Gama glutamil transferaza)' FROM analiza_standard WHERE cod_standard='GGT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gama-glutamil transferaza' FROM analiza_standard WHERE cod_standard='GGT' ON CONFLICT (alias) DO NOTHING;

-- ── Fosfataza alcalina ─────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fosfataza alcalina' FROM analiza_standard WHERE cod_standard='ALP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fosfataza alcalină' FROM analiza_standard WHERE cod_standard='ALP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALP' FROM analiza_standard WHERE cod_standard='ALP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FA' FROM analiza_standard WHERE cod_standard='ALP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alkaline Phosphatase' FROM analiza_standard WHERE cod_standard='ALP' ON CONFLICT (alias) DO NOTHING;

-- ── HbA1c ──────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina glicata' FROM analiza_standard WHERE cod_standard='HBA1C' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina glicată' FROM analiza_standard WHERE cod_standard='HBA1C' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HbA1c' FROM analiza_standard WHERE cod_standard='HBA1C' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HBA1C' FROM analiza_standard WHERE cod_standard='HBA1C' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'A1C' FROM analiza_standard WHERE cod_standard='HBA1C' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glycated hemoglobin' FROM analiza_standard WHERE cod_standard='HBA1C' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina A1c' FROM analiza_standard WHERE cod_standard='HBA1C' ON CONFLICT (alias) DO NOTHING;

-- ── Colesterol total ───────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol total' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cholesterol' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cholesterol total' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CHOL' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CT' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL' ON CONFLICT (alias) DO NOTHING;

-- ── HDL ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HDL' FROM analiza_standard WHERE cod_standard='HDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HDL colesterol' FROM analiza_standard WHERE cod_standard='HDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HDL-C' FROM analiza_standard WHERE cod_standard='HDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol HDL' FROM analiza_standard WHERE cod_standard='HDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HDL Cholesterol' FROM analiza_standard WHERE cod_standard='HDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol HDL (col. bun)' FROM analiza_standard WHERE cod_standard='HDL' ON CONFLICT (alias) DO NOTHING;

-- ── LDL ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL' FROM analiza_standard WHERE cod_standard='LDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL colesterol' FROM analiza_standard WHERE cod_standard='LDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL-C' FROM analiza_standard WHERE cod_standard='LDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol LDL' FROM analiza_standard WHERE cod_standard='LDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL Cholesterol' FROM analiza_standard WHERE cod_standard='LDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL-colesterol' FROM analiza_standard WHERE cod_standard='LDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol LDL calculat' FROM analiza_standard WHERE cod_standard='LDL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL col. calculat' FROM analiza_standard WHERE cod_standard='LDL' ON CONFLICT (alias) DO NOTHING;

-- ── Trigliceride ───────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Trigliceride' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Triglycerides' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TG' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TRIG' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Trigliceridele serice' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE' ON CONFLICT (alias) DO NOTHING;

-- ── TSH ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TSH' FROM analiza_standard WHERE cod_standard='TSH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TSH bazal' FROM analiza_standard WHERE cod_standard='TSH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TSH (hormon hipofizar tireostimulator bazal)' FROM analiza_standard WHERE cod_standard='TSH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Thyroid Stimulating Hormone' FROM analiza_standard WHERE cod_standard='TSH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Tireotropina' FROM analiza_standard WHERE cod_standard='TSH' ON CONFLICT (alias) DO NOTHING;

-- ── FT4 ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FT4' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'T4 liber' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'T4 Liber' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Tiroxina libera' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Free T4' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;

-- ── FT3 ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FT3' FROM analiza_standard WHERE cod_standard='FT3' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'T3 liber' FROM analiza_standard WHERE cod_standard='FT3' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'T3 Liber' FROM analiza_standard WHERE cod_standard='FT3' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Free T3' FROM analiza_standard WHERE cod_standard='FT3' ON CONFLICT (alias) DO NOTHING;

-- ── Anti-TPO ───────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Anti-TPO' FROM analiza_standard WHERE cod_standard='ANTI_TPO' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'AntiTPO' FROM analiza_standard WHERE cod_standard='ANTI_TPO' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ac anti-TPO' FROM analiza_standard WHERE cod_standard='ANTI_TPO' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Anticorpi anti-peroxidaza tiroidiana' FROM analiza_standard WHERE cod_standard='ANTI_TPO' ON CONFLICT (alias) DO NOTHING;

-- ── CRP ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CRP' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CRP cantitativ' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteina C reactiva' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteina C reactiva (PCR)' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'C-Reactive Protein' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PCR cantitativ' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CRP (Proteina C Reactiva)' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;

-- ── hs-CRP ─────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'hs-CRP' FROM analiza_standard WHERE cod_standard='CRP_HS' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'hsCRP' FROM analiza_standard WHERE cod_standard='CRP_HS' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CRP ultrasensibil' FROM analiza_standard WHERE cod_standard='CRP_HS' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CRP high sensitivity' FROM analiza_standard WHERE cod_standard='CRP_HS' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteina C reactiva ultrasensibila' FROM analiza_standard WHERE cod_standard='CRP_HS' ON CONFLICT (alias) DO NOTHING;

-- ── VSH ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'VSH' FROM analiza_standard WHERE cod_standard='VSH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Viteza de sedimentare' FROM analiza_standard WHERE cod_standard='VSH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Viteza sedimentare hematii' FROM analiza_standard WHERE cod_standard='VSH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ESR' FROM analiza_standard WHERE cod_standard='VSH' ON CONFLICT (alias) DO NOTHING;

-- ── Fibrinogen ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fibrinogen' FROM analiza_standard WHERE cod_standard='FIBRINOGEN' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fibrinogen plasmatic' FROM analiza_standard WHERE cod_standard='FIBRINOGEN' ON CONFLICT (alias) DO NOTHING;

-- ── INR ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'INR' FROM analiza_standard WHERE cod_standard='INR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'International Normalized Ratio' FROM analiza_standard WHERE cod_standard='INR' ON CONFLICT (alias) DO NOTHING;

-- ── PT ─────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PT' FROM analiza_standard WHERE cod_standard='PT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Timp de protrombina' FROM analiza_standard WHERE cod_standard='PT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Timp de protrombina (TP)' FROM analiza_standard WHERE cod_standard='PT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Prothrombin Time' FROM analiza_standard WHERE cod_standard='PT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TP' FROM analiza_standard WHERE cod_standard='PT' ON CONFLICT (alias) DO NOTHING;

-- ── aPTT ───────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'aPTT' FROM analiza_standard WHERE cod_standard='APTT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'APTT' FROM analiza_standard WHERE cod_standard='APTT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PTT activat' FROM analiza_standard WHERE cod_standard='APTT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Activated Partial Thromboplastin Time' FROM analiza_standard WHERE cod_standard='APTT' ON CONFLICT (alias) DO NOTHING;

-- ── D-Dimeri ───────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'D-dimeri' FROM analiza_standard WHERE cod_standard='D_DIMERI' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'D-Dimers' FROM analiza_standard WHERE cod_standard='D_DIMERI' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'D dimeri' FROM analiza_standard WHERE cod_standard='D_DIMERI' ON CONFLICT (alias) DO NOTHING;

-- ── Fier seric ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fier seric' FROM analiza_standard WHERE cod_standard='FIER' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fier' FROM analiza_standard WHERE cod_standard='FIER' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Iron' FROM analiza_standard WHERE cod_standard='FIER' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fe' FROM analiza_standard WHERE cod_standard='FIER' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Sideremie' FROM analiza_standard WHERE cod_standard='FIER' ON CONFLICT (alias) DO NOTHING;

-- ── Feritina ───────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Feritina' FROM analiza_standard WHERE cod_standard='FERITINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ferritin' FROM analiza_standard WHERE cod_standard='FERITINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ferritina' FROM analiza_standard WHERE cod_standard='FERITINA' ON CONFLICT (alias) DO NOTHING;

-- ── Vitamina D ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamina D' FROM analiza_standard WHERE cod_standard='VIT_D' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamina D3' FROM analiza_standard WHERE cod_standard='VIT_D' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '25-OH Vitamina D' FROM analiza_standard WHERE cod_standard='VIT_D' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '25-OH-D3' FROM analiza_standard WHERE cod_standard='VIT_D' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '25(OH)D' FROM analiza_standard WHERE cod_standard='VIT_D' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamin D' FROM analiza_standard WHERE cod_standard='VIT_D' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamina D (25-hidroxicolecalciferol)' FROM analiza_standard WHERE cod_standard='VIT_D' ON CONFLICT (alias) DO NOTHING;

-- ── Vitamina B12 ───────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamina B12' FROM analiza_standard WHERE cod_standard='VIT_B12' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'B12' FROM analiza_standard WHERE cod_standard='VIT_B12' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cobalamina' FROM analiza_standard WHERE cod_standard='VIT_B12' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamin B12' FROM analiza_standard WHERE cod_standard='VIT_B12' ON CONFLICT (alias) DO NOTHING;

-- ── Acid folic ─────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Acid folic' FROM analiza_standard WHERE cod_standard='ACID_FOLIC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Folat' FROM analiza_standard WHERE cod_standard='ACID_FOLIC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Folic acid' FROM analiza_standard WHERE cod_standard='ACID_FOLIC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamina B9' FROM analiza_standard WHERE cod_standard='ACID_FOLIC' ON CONFLICT (alias) DO NOTHING;

-- ── Sodiu, Potasiu, Calciu ─────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Sodiu' FROM analiza_standard WHERE cod_standard='SODIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Sodium' FROM analiza_standard WHERE cod_standard='SODIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Na' FROM analiza_standard WHERE cod_standard='SODIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Potasiu' FROM analiza_standard WHERE cod_standard='POTASIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Potassium' FROM analiza_standard WHERE cod_standard='POTASIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Kaliu' FROM analiza_standard WHERE cod_standard='POTASIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'K' FROM analiza_standard WHERE cod_standard='POTASIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Calciu' FROM analiza_standard WHERE cod_standard='CALCIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Calcium' FROM analiza_standard WHERE cod_standard='CALCIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ca' FROM analiza_standard WHERE cod_standard='CALCIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Calciu seric' FROM analiza_standard WHERE cod_standard='CALCIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Magneziu' FROM analiza_standard WHERE cod_standard='MAGNEZIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Magnesium' FROM analiza_standard WHERE cod_standard='MAGNEZIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mg' FROM analiza_standard WHERE cod_standard='MAGNEZIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fosfor' FROM analiza_standard WHERE cod_standard='FOSFOR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Phosphorus' FROM analiza_standard WHERE cod_standard='FOSFOR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Phosphate' FROM analiza_standard WHERE cod_standard='FOSFOR' ON CONFLICT (alias) DO NOTHING;

-- ── PSA ────────────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PSA total' FROM analiza_standard WHERE cod_standard='PSA_TOTAL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PSA' FROM analiza_standard WHERE cod_standard='PSA_TOTAL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Antigen specific prostatic' FROM analiza_standard WHERE cod_standard='PSA_TOTAL' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PSA liber' FROM analiza_standard WHERE cod_standard='PSA_LIBER' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Free PSA' FROM analiza_standard WHERE cod_standard='PSA_LIBER' ON CONFLICT (alias) DO NOTHING;

-- ── Electroforeza proteine ─────────────────────────────────────────────────
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('ELECTRO_ALB',    'Electroforeza – Albumina'),
('ELECTRO_ALFA1',  'Electroforeza – Alfa 1 globulina'),
('ELECTRO_ALFA2',  'Electroforeza – Alfa 2 globulina'),
('ELECTRO_BETA1',  'Electroforeza – Beta 1 globulina'),
('ELECTRO_BETA2',  'Electroforeza – Beta 2 globulina'),
('ELECTRO_GAMA',   'Electroforeza – Gama globulina'),
('ELECTRO_RAPORT', 'Raport A/G (electroforeza)') ON CONFLICT (cod_standard) DO NOTHING;

INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumina%' FROM analiza_standard WHERE cod_standard='ELECTRO_ALB' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumina %' FROM analiza_standard WHERE cod_standard='ELECTRO_ALB' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alfa 1 globulina %' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA1' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alfa 1' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA1' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alpha 1' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA1' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alfa 2 globulina %' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA2' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alfa 2' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA2' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alpha 2' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA2' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Beta 1 globulina %' FROM analiza_standard WHERE cod_standard='ELECTRO_BETA1' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Beta 1' FROM analiza_standard WHERE cod_standard='ELECTRO_BETA1' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Beta 2 globulina' FROM analiza_standard WHERE cod_standard='ELECTRO_BETA2' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Beta 2' FROM analiza_standard WHERE cod_standard='ELECTRO_BETA2' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gamma globulina' FROM analiza_standard WHERE cod_standard='ELECTRO_GAMA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gama globulina' FROM analiza_standard WHERE cod_standard='ELECTRO_GAMA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gamma globulina %' FROM analiza_standard WHERE cod_standard='ELECTRO_GAMA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Raport A/G' FROM analiza_standard WHERE cod_standard='ELECTRO_RAPORT' ON CONFLICT (alias) DO NOTHING;

