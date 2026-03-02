-- Migrare 002: analize standard extinse + alias-uri din laboratoare romanesti
-- Laboratoare acoperite: Bioclinica, MedLife, Synevo, Medicover, Regina Maria
-- Foloseste INSERT OR IGNORE pentru a nu duplica date existente.

-- ─── Tabel analize necunoscute (auto-invatare) ──────────────────────────────
CREATE TABLE IF NOT EXISTS analiza_necunoscuta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    denumire_raw TEXT NOT NULL UNIQUE,
    aparitii INTEGER NOT NULL DEFAULT 1,
    aprobata INTEGER NOT NULL DEFAULT 0,       -- 0=neaprobata, 1=aprobata si mapata
    analiza_standard_id INTEGER REFERENCES analiza_standard(id) ON DELETE SET NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_necunoscute_raw ON analiza_necunoscuta(denumire_raw);

-- ─── Analize standard (extinse) ──────────────────────────────────────────────

-- Hemoleucograma
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
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
('BAZOFILE_NR',     'Bazofile (numar absolut)');

-- Biochimie generala
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
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
('EGFR',            'RFG estimat (eGFR)');

-- Enzime hepatice
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
('ALT',    'ALAT (TGP)'),
('AST',    'ASAT (TGO)'),
('GGT',    'GGT – Gama glutamil transferaza'),
('ALP',    'Fosfataza alcalina'),
('HBA1C',  'Hemoglobina glicata (HbA1c)');

-- Lipide
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
('COLESTEROL_TOTAL', 'Colesterol total'),
('HDL',              'HDL colesterol'),
('LDL',              'LDL colesterol'),
('TRIGLICERIDE',     'Trigliceride'),
('NON_HDL',          'Non-HDL colesterol'),
('LPDL',             'Lp(a) – Lipoproteina a');

-- Electrolyti & minerale
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
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
('ZINC',     'Zinc seric');

-- Hormoni tiroidieni
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
('TSH',      'TSH'),
('FT4',      'T4 liber (FT4)'),
('FT3',      'T3 liber (FT3)'),
('T4',       'T4 total'),
('T3',       'T3 total'),
('ANTI_TPO', 'Anticorpi anti-TPO'),
('ANTI_TG',  'Anticorpi anti-tiroglobulina'),
('TG',       'Tiroglobulina');

-- Hormoni sexuali si suprarenali
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
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
('BETA_HCG',    'Beta-hCG');

-- Inflamatie si imunologie
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
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
('ANTI_CCP',     'Anticorpi anti-CCP');

-- Coagulare
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
('PT',           'Timp de protrombina (PT)'),
('INR',          'INR'),
('APTT',         'aPTT – Timp partial de tromboplastina activata'),
('TT',           'Timp de trombina'),
('D_DIMERI',     'D-dimeri');

-- Markeri tumorali
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
('CEA',          'CEA – Antigen carcino-embrionar'),
('CA_125',       'CA 125'),
('CA_19_9',      'CA 19-9'),
('CA_15_3',      'CA 15-3'),
('AFP',          'Alfa-fetoproteina (AFP)'),
('CA_72_4',      'CA 72-4');

-- Serologie infectioasa
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
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
('RUBELLA_IGM',  'Rubeola IgM');

-- Urina
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
('URINA_SUMAR',   'Sumar urina (examen complet)'),
('MICROALBUMIN',  'Microalbuminurie'),
('CREAT_URINA',   'Creatinina urinara');

-- ─── ALIAS-URI ────────────────────────────────────────────────────────────────
-- Format: INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias)
--         SELECT id, 'alias' FROM analiza_standard WHERE cod_standard = 'COD';

-- ── Leucocite ──────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Leucocite' FROM analiza_standard WHERE cod_standard='WBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'WBC' FROM analiza_standard WHERE cod_standard='WBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. leucocite' FROM analiza_standard WHERE cod_standard='WBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar leucocite' FROM analiza_standard WHERE cod_standard='WBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Globule albe' FROM analiza_standard WHERE cod_standard='WBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LEU' FROM analiza_standard WHERE cod_standard='WBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'White Blood Cells' FROM analiza_standard WHERE cod_standard='WBC';

-- ── Eritrocite ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eritrocite' FROM analiza_standard WHERE cod_standard='RBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RBC' FROM analiza_standard WHERE cod_standard='RBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. eritrocite' FROM analiza_standard WHERE cod_standard='RBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar eritrocite' FROM analiza_standard WHERE cod_standard='RBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Globule rosii' FROM analiza_standard WHERE cod_standard='RBC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Red Blood Cells' FROM analiza_standard WHERE cod_standard='RBC';

-- ── Hemoglobina ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina' FROM analiza_standard WHERE cod_standard='HB';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobină' FROM analiza_standard WHERE cod_standard='HB';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HGB' FROM analiza_standard WHERE cod_standard='HB';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hb' FROM analiza_standard WHERE cod_standard='HB';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Haemoglobin' FROM analiza_standard WHERE cod_standard='HB';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobin' FROM analiza_standard WHERE cod_standard='HB';

-- ── Hematocrit ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hematocrit' FROM analiza_standard WHERE cod_standard='HCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HCT' FROM analiza_standard WHERE cod_standard='HCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ht' FROM analiza_standard WHERE cod_standard='HCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Haematocrit' FROM analiza_standard WHERE cod_standard='HCT';

-- ── MCV / VEM ──────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'VEM' FROM analiza_standard WHERE cod_standard='MCV';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MCV' FROM analiza_standard WHERE cod_standard='MCV';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Volum eritrocitar mediu' FROM analiza_standard WHERE cod_standard='MCV';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mean Corpuscular Volume' FROM analiza_standard WHERE cod_standard='MCV';

-- ── MCH / HEM ──────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MCH' FROM analiza_standard WHERE cod_standard='MCH';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HEM' FROM analiza_standard WHERE cod_standard='MCH';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina eritrocitara medie' FROM analiza_standard WHERE cod_standard='MCH';

-- ── MCHC / CHEM ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MCHC' FROM analiza_standard WHERE cod_standard='MCHC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CHEM' FROM analiza_standard WHERE cod_standard='MCHC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Concentratia Hb eritrocitare' FROM analiza_standard WHERE cod_standard='MCHC';

-- ── RDW ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RDW' FROM analiza_standard WHERE cod_standard='RDW';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RDW-CV' FROM analiza_standard WHERE cod_standard='RDW';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RDW-SD' FROM analiza_standard WHERE cod_standard='RDW';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Indice distributie eritrocite' FROM analiza_standard WHERE cod_standard='RDW';

-- ── Trombocite ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Trombocite' FROM analiza_standard WHERE cod_standard='PLT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PLT' FROM analiza_standard WHERE cod_standard='PLT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. trombocite' FROM analiza_standard WHERE cod_standard='PLT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar trombocite' FROM analiza_standard WHERE cod_standard='PLT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Platelets' FROM analiza_standard WHERE cod_standard='PLT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Plaquettes' FROM analiza_standard WHERE cod_standard='PLT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Plachete' FROM analiza_standard WHERE cod_standard='PLT';

-- ── MPV / VTM ──────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MPV' FROM analiza_standard WHERE cod_standard='MPV';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'VTM' FROM analiza_standard WHERE cod_standard='MPV';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Volum trombocitar mediu' FROM analiza_standard WHERE cod_standard='MPV';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mean Platelet Volume' FROM analiza_standard WHERE cod_standard='MPV';

-- ── PDW ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PDW' FROM analiza_standard WHERE cod_standard='PDW';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Platelet Distribution Width' FROM analiza_standard WHERE cod_standard='PDW';

-- ── PCT ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PCT' FROM analiza_standard WHERE cod_standard='PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Trombocrit' FROM analiza_standard WHERE cod_standard='PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Plateletcrit' FROM analiza_standard WHERE cod_standard='PCT';

-- ── Neutrofile % ───────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, '% Neutrofile' FROM analiza_standard WHERE cod_standard='NEUTROFILE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Neutrofile %' FROM analiza_standard WHERE cod_standard='NEUTROFILE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'NEUT%' FROM analiza_standard WHERE cod_standard='NEUTROFILE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Neutrophils %' FROM analiza_standard WHERE cod_standard='NEUTROFILE_PCT';

-- ── Neutrofile absolut ─────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. neutrofile' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Neutrofile' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'NEUT#' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Neutrophils' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR';

-- ── Limfocite % ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, '% Limfocite' FROM analiza_standard WHERE cod_standard='LIMFOCITE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Limfocite %' FROM analiza_standard WHERE cod_standard='LIMFOCITE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LYM%' FROM analiza_standard WHERE cod_standard='LIMFOCITE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Lymphocytes %' FROM analiza_standard WHERE cod_standard='LIMFOCITE_PCT';

-- ── Limfocite absolut ──────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. limfocite' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Limfocite' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LYM#' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Lymphocytes' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR';

-- ── Monocite % ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, '% Monocite' FROM analiza_standard WHERE cod_standard='MONOCITE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Monocite %' FROM analiza_standard WHERE cod_standard='MONOCITE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MON%' FROM analiza_standard WHERE cod_standard='MONOCITE_PCT';

-- ── Monocite absolut ───────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. monocite' FROM analiza_standard WHERE cod_standard='MONOCITE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Monocite' FROM analiza_standard WHERE cod_standard='MONOCITE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MON#' FROM analiza_standard WHERE cod_standard='MONOCITE_NR';

-- ── Eozinofile % ───────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, '% Eozinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eozinofile %' FROM analiza_standard WHERE cod_standard='EOZINOFILE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'EOS%' FROM analiza_standard WHERE cod_standard='EOZINOFILE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eosinofile %' FROM analiza_standard WHERE cod_standard='EOZINOFILE_PCT';

-- ── Eozinofile absolut ─────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. eozinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eozinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'EOS#' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eosinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR';

-- ── Bazofile % ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, '% Basofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bazofile %' FROM analiza_standard WHERE cod_standard='BAZOFILE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Basofile %' FROM analiza_standard WHERE cod_standard='BAZOFILE_PCT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'BAS%' FROM analiza_standard WHERE cod_standard='BAZOFILE_PCT';

-- ── Bazofile absolut ───────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. basofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Nr. bazofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bazofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Basofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'BAS#' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR';

-- ── Glicemie ───────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glicemie' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoza' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoză' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucose' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'GLU' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoza serica' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glucoza serică' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glicemie a jeun' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glicemie la nemâncat' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING';

-- ── Uree ───────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Uree' FROM analiza_standard WHERE cod_standard='UREE';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Uree serica' FROM analiza_standard WHERE cod_standard='UREE';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Uree serică' FROM analiza_standard WHERE cod_standard='UREE';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Urea' FROM analiza_standard WHERE cod_standard='UREE';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'BUN' FROM analiza_standard WHERE cod_standard='UREE';

-- ── Creatinina ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina' FROM analiza_standard WHERE cod_standard='CREATININA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinină' FROM analiza_standard WHERE cod_standard='CREATININA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinine' FROM analiza_standard WHERE cod_standard='CREATININA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CREAT' FROM analiza_standard WHERE cod_standard='CREATININA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina serica' FROM analiza_standard WHERE cod_standard='CREATININA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina serică' FROM analiza_standard WHERE cod_standard='CREATININA';

-- ── Acid uric ──────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Acid uric' FROM analiza_standard WHERE cod_standard='ACID_URIC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Uric acid' FROM analiza_standard WHERE cod_standard='ACID_URIC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'AU' FROM analiza_standard WHERE cod_standard='ACID_URIC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Guta - acid uric' FROM analiza_standard WHERE cod_standard='ACID_URIC';

-- ── Proteine totale ────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteine totale' FROM analiza_standard WHERE cod_standard='PROTEINE_TOT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteine totale serice' FROM analiza_standard WHERE cod_standard='PROTEINE_TOT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Total Protein' FROM analiza_standard WHERE cod_standard='PROTEINE_TOT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TP' FROM analiza_standard WHERE cod_standard='PROTEINE_TOT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteine' FROM analiza_standard WHERE cod_standard='PROTEINE_TOT';

-- ── Albumina ───────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumina' FROM analiza_standard WHERE cod_standard='ALBUMINA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumină' FROM analiza_standard WHERE cod_standard='ALBUMINA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumin' FROM analiza_standard WHERE cod_standard='ALBUMINA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALB' FROM analiza_standard WHERE cod_standard='ALBUMINA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumina serica' FROM analiza_standard WHERE cod_standard='ALBUMINA';

-- ── Bilirubina ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina totala' FROM analiza_standard WHERE cod_standard='BILIRUBIN_TOT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina totală' FROM analiza_standard WHERE cod_standard='BILIRUBIN_TOT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubin total' FROM analiza_standard WHERE cod_standard='BILIRUBIN_TOT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'BIL-T' FROM analiza_standard WHERE cod_standard='BILIRUBIN_TOT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TBIL' FROM analiza_standard WHERE cod_standard='BILIRUBIN_TOT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina directa' FROM analiza_standard WHERE cod_standard='BILIRUBIN_DIR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina directă' FROM analiza_standard WHERE cod_standard='BILIRUBIN_DIR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubin direct' FROM analiza_standard WHERE cod_standard='BILIRUBIN_DIR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'DBIL' FROM analiza_standard WHERE cod_standard='BILIRUBIN_DIR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'BIL-D' FROM analiza_standard WHERE cod_standard='BILIRUBIN_DIR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina indirecta' FROM analiza_standard WHERE cod_standard='BILIRUBIN_IND';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bilirubina indirectă' FROM analiza_standard WHERE cod_standard='BILIRUBIN_IND';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'IBIL' FROM analiza_standard WHERE cod_standard='BILIRUBIN_IND';

-- ── ALAT / TGP ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALAT' FROM analiza_standard WHERE cod_standard='ALT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALT' FROM analiza_standard WHERE cod_standard='ALT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGP' FROM analiza_standard WHERE cod_standard='ALT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGP (ALAT)' FROM analiza_standard WHERE cod_standard='ALT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALT (ALAT)' FROM analiza_standard WHERE cod_standard='ALT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alanin aminotransferaza' FROM analiza_standard WHERE cod_standard='ALT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alanine Aminotransferase' FROM analiza_standard WHERE cod_standard='ALT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'GPT' FROM analiza_standard WHERE cod_standard='ALT';

-- ── ASAT / TGO ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ASAT' FROM analiza_standard WHERE cod_standard='AST';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'AST' FROM analiza_standard WHERE cod_standard='AST';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGO' FROM analiza_standard WHERE cod_standard='AST';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGO (ASAT)' FROM analiza_standard WHERE cod_standard='AST';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'AST (ASAT)' FROM analiza_standard WHERE cod_standard='AST';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Aspartat aminotransferaza' FROM analiza_standard WHERE cod_standard='AST';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Aspartate Aminotransferase' FROM analiza_standard WHERE cod_standard='AST';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'GOT' FROM analiza_standard WHERE cod_standard='AST';

-- ── GGT ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'GGT' FROM analiza_standard WHERE cod_standard='GGT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gama GT' FROM analiza_standard WHERE cod_standard='GGT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gamma GT' FROM analiza_standard WHERE cod_standard='GGT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gamma-GT' FROM analiza_standard WHERE cod_standard='GGT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'GGT (Gama glutamil transferaza)' FROM analiza_standard WHERE cod_standard='GGT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gama-glutamil transferaza' FROM analiza_standard WHERE cod_standard='GGT';

-- ── Fosfataza alcalina ─────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fosfataza alcalina' FROM analiza_standard WHERE cod_standard='ALP';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fosfataza alcalină' FROM analiza_standard WHERE cod_standard='ALP';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALP' FROM analiza_standard WHERE cod_standard='ALP';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FA' FROM analiza_standard WHERE cod_standard='ALP';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alkaline Phosphatase' FROM analiza_standard WHERE cod_standard='ALP';

-- ── HbA1c ──────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina glicata' FROM analiza_standard WHERE cod_standard='HBA1C';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina glicată' FROM analiza_standard WHERE cod_standard='HBA1C';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HbA1c' FROM analiza_standard WHERE cod_standard='HBA1C';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HBA1C' FROM analiza_standard WHERE cod_standard='HBA1C';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'A1C' FROM analiza_standard WHERE cod_standard='HBA1C';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glycated hemoglobin' FROM analiza_standard WHERE cod_standard='HBA1C';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Hemoglobina A1c' FROM analiza_standard WHERE cod_standard='HBA1C';

-- ── Colesterol total ───────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol total' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cholesterol' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cholesterol total' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CHOL' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CT' FROM analiza_standard WHERE cod_standard='COLESTEROL_TOTAL';

-- ── HDL ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HDL' FROM analiza_standard WHERE cod_standard='HDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HDL colesterol' FROM analiza_standard WHERE cod_standard='HDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HDL-C' FROM analiza_standard WHERE cod_standard='HDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol HDL' FROM analiza_standard WHERE cod_standard='HDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HDL Cholesterol' FROM analiza_standard WHERE cod_standard='HDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol HDL (col. bun)' FROM analiza_standard WHERE cod_standard='HDL';

-- ── LDL ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL' FROM analiza_standard WHERE cod_standard='LDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL colesterol' FROM analiza_standard WHERE cod_standard='LDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL-C' FROM analiza_standard WHERE cod_standard='LDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol LDL' FROM analiza_standard WHERE cod_standard='LDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL Cholesterol' FROM analiza_standard WHERE cod_standard='LDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL-colesterol' FROM analiza_standard WHERE cod_standard='LDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Colesterol LDL calculat' FROM analiza_standard WHERE cod_standard='LDL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'LDL col. calculat' FROM analiza_standard WHERE cod_standard='LDL';

-- ── Trigliceride ───────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Trigliceride' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Triglycerides' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TG' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TRIG' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Trigliceridele serice' FROM analiza_standard WHERE cod_standard='TRIGLICERIDE';

-- ── TSH ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TSH' FROM analiza_standard WHERE cod_standard='TSH';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TSH bazal' FROM analiza_standard WHERE cod_standard='TSH';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TSH (hormon hipofizar tireostimulator bazal)' FROM analiza_standard WHERE cod_standard='TSH';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Thyroid Stimulating Hormone' FROM analiza_standard WHERE cod_standard='TSH';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Tireotropina' FROM analiza_standard WHERE cod_standard='TSH';

-- ── FT4 ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FT4' FROM analiza_standard WHERE cod_standard='FT4';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'T4 liber' FROM analiza_standard WHERE cod_standard='FT4';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'T4 Liber' FROM analiza_standard WHERE cod_standard='FT4';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Tiroxina libera' FROM analiza_standard WHERE cod_standard='FT4';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Free T4' FROM analiza_standard WHERE cod_standard='FT4';

-- ── FT3 ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FT3' FROM analiza_standard WHERE cod_standard='FT3';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'T3 liber' FROM analiza_standard WHERE cod_standard='FT3';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'T3 Liber' FROM analiza_standard WHERE cod_standard='FT3';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Free T3' FROM analiza_standard WHERE cod_standard='FT3';

-- ── Anti-TPO ───────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Anti-TPO' FROM analiza_standard WHERE cod_standard='ANTI_TPO';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'AntiTPO' FROM analiza_standard WHERE cod_standard='ANTI_TPO';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ac anti-TPO' FROM analiza_standard WHERE cod_standard='ANTI_TPO';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Anticorpi anti-peroxidaza tiroidiana' FROM analiza_standard WHERE cod_standard='ANTI_TPO';

-- ── CRP ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CRP' FROM analiza_standard WHERE cod_standard='CRP';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CRP cantitativ' FROM analiza_standard WHERE cod_standard='CRP';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteina C reactiva' FROM analiza_standard WHERE cod_standard='CRP';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteina C reactiva (PCR)' FROM analiza_standard WHERE cod_standard='CRP';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'C-Reactive Protein' FROM analiza_standard WHERE cod_standard='CRP';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PCR cantitativ' FROM analiza_standard WHERE cod_standard='CRP';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CRP (Proteina C Reactiva)' FROM analiza_standard WHERE cod_standard='CRP';

-- ── hs-CRP ─────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'hs-CRP' FROM analiza_standard WHERE cod_standard='CRP_HS';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'hsCRP' FROM analiza_standard WHERE cod_standard='CRP_HS';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CRP ultrasensibil' FROM analiza_standard WHERE cod_standard='CRP_HS';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'CRP high sensitivity' FROM analiza_standard WHERE cod_standard='CRP_HS';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Proteina C reactiva ultrasensibila' FROM analiza_standard WHERE cod_standard='CRP_HS';

-- ── VSH ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'VSH' FROM analiza_standard WHERE cod_standard='VSH';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Viteza de sedimentare' FROM analiza_standard WHERE cod_standard='VSH';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Viteza sedimentare hematii' FROM analiza_standard WHERE cod_standard='VSH';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ESR' FROM analiza_standard WHERE cod_standard='VSH';

-- ── Fibrinogen ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fibrinogen' FROM analiza_standard WHERE cod_standard='FIBRINOGEN';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fibrinogen plasmatic' FROM analiza_standard WHERE cod_standard='FIBRINOGEN';

-- ── INR ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'INR' FROM analiza_standard WHERE cod_standard='INR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'International Normalized Ratio' FROM analiza_standard WHERE cod_standard='INR';

-- ── PT ─────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PT' FROM analiza_standard WHERE cod_standard='PT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Timp de protrombina' FROM analiza_standard WHERE cod_standard='PT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Timp de protrombina (TP)' FROM analiza_standard WHERE cod_standard='PT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Prothrombin Time' FROM analiza_standard WHERE cod_standard='PT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TP' FROM analiza_standard WHERE cod_standard='PT';

-- ── aPTT ───────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'aPTT' FROM analiza_standard WHERE cod_standard='APTT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'APTT' FROM analiza_standard WHERE cod_standard='APTT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PTT activat' FROM analiza_standard WHERE cod_standard='APTT';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Activated Partial Thromboplastin Time' FROM analiza_standard WHERE cod_standard='APTT';

-- ── D-Dimeri ───────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'D-dimeri' FROM analiza_standard WHERE cod_standard='D_DIMERI';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'D-Dimers' FROM analiza_standard WHERE cod_standard='D_DIMERI';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'D dimeri' FROM analiza_standard WHERE cod_standard='D_DIMERI';

-- ── Fier seric ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fier seric' FROM analiza_standard WHERE cod_standard='FIER';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fier' FROM analiza_standard WHERE cod_standard='FIER';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Iron' FROM analiza_standard WHERE cod_standard='FIER';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fe' FROM analiza_standard WHERE cod_standard='FIER';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Sideremie' FROM analiza_standard WHERE cod_standard='FIER';

-- ── Feritina ───────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Feritina' FROM analiza_standard WHERE cod_standard='FERITINA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ferritin' FROM analiza_standard WHERE cod_standard='FERITINA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ferritina' FROM analiza_standard WHERE cod_standard='FERITINA';

-- ── Vitamina D ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamina D' FROM analiza_standard WHERE cod_standard='VIT_D';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamina D3' FROM analiza_standard WHERE cod_standard='VIT_D';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, '25-OH Vitamina D' FROM analiza_standard WHERE cod_standard='VIT_D';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, '25-OH-D3' FROM analiza_standard WHERE cod_standard='VIT_D';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, '25(OH)D' FROM analiza_standard WHERE cod_standard='VIT_D';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamin D' FROM analiza_standard WHERE cod_standard='VIT_D';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamina D (25-hidroxicolecalciferol)' FROM analiza_standard WHERE cod_standard='VIT_D';

-- ── Vitamina B12 ───────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamina B12' FROM analiza_standard WHERE cod_standard='VIT_B12';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'B12' FROM analiza_standard WHERE cod_standard='VIT_B12';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Cobalamina' FROM analiza_standard WHERE cod_standard='VIT_B12';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamin B12' FROM analiza_standard WHERE cod_standard='VIT_B12';

-- ── Acid folic ─────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Acid folic' FROM analiza_standard WHERE cod_standard='ACID_FOLIC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Folat' FROM analiza_standard WHERE cod_standard='ACID_FOLIC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Folic acid' FROM analiza_standard WHERE cod_standard='ACID_FOLIC';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Vitamina B9' FROM analiza_standard WHERE cod_standard='ACID_FOLIC';

-- ── Sodiu, Potasiu, Calciu ─────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Sodiu' FROM analiza_standard WHERE cod_standard='SODIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Sodium' FROM analiza_standard WHERE cod_standard='SODIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Na' FROM analiza_standard WHERE cod_standard='SODIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Potasiu' FROM analiza_standard WHERE cod_standard='POTASIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Potassium' FROM analiza_standard WHERE cod_standard='POTASIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Kaliu' FROM analiza_standard WHERE cod_standard='POTASIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'K' FROM analiza_standard WHERE cod_standard='POTASIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Calciu' FROM analiza_standard WHERE cod_standard='CALCIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Calcium' FROM analiza_standard WHERE cod_standard='CALCIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ca' FROM analiza_standard WHERE cod_standard='CALCIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Calciu seric' FROM analiza_standard WHERE cod_standard='CALCIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Magneziu' FROM analiza_standard WHERE cod_standard='MAGNEZIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Magnesium' FROM analiza_standard WHERE cod_standard='MAGNEZIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Mg' FROM analiza_standard WHERE cod_standard='MAGNEZIU';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Fosfor' FROM analiza_standard WHERE cod_standard='FOSFOR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Phosphorus' FROM analiza_standard WHERE cod_standard='FOSFOR';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Phosphate' FROM analiza_standard WHERE cod_standard='FOSFOR';

-- ── PSA ────────────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PSA total' FROM analiza_standard WHERE cod_standard='PSA_TOTAL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PSA' FROM analiza_standard WHERE cod_standard='PSA_TOTAL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Antigen specific prostatic' FROM analiza_standard WHERE cod_standard='PSA_TOTAL';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PSA liber' FROM analiza_standard WHERE cod_standard='PSA_LIBER';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Free PSA' FROM analiza_standard WHERE cod_standard='PSA_LIBER';

-- ── Electroforeza proteine ─────────────────────────────────────────────────
INSERT OR IGNORE INTO analiza_standard (cod_standard, denumire_standard) VALUES
('ELECTRO_ALB',    'Electroforeza – Albumina'),
('ELECTRO_ALFA1',  'Electroforeza – Alfa 1 globulina'),
('ELECTRO_ALFA2',  'Electroforeza – Alfa 2 globulina'),
('ELECTRO_BETA1',  'Electroforeza – Beta 1 globulina'),
('ELECTRO_BETA2',  'Electroforeza – Beta 2 globulina'),
('ELECTRO_GAMA',   'Electroforeza – Gama globulina'),
('ELECTRO_RAPORT', 'Raport A/G (electroforeza)');

INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumina%' FROM analiza_standard WHERE cod_standard='ELECTRO_ALB';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Albumina %' FROM analiza_standard WHERE cod_standard='ELECTRO_ALB';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alfa 1 globulina %' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA1';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alfa 1' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA1';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alpha 1' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA1';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alfa 2 globulina %' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA2';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alfa 2' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA2';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Alpha 2' FROM analiza_standard WHERE cod_standard='ELECTRO_ALFA2';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Beta 1 globulina %' FROM analiza_standard WHERE cod_standard='ELECTRO_BETA1';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Beta 1' FROM analiza_standard WHERE cod_standard='ELECTRO_BETA1';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Beta 2 globulina' FROM analiza_standard WHERE cod_standard='ELECTRO_BETA2';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Beta 2' FROM analiza_standard WHERE cod_standard='ELECTRO_BETA2';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gamma globulina' FROM analiza_standard WHERE cod_standard='ELECTRO_GAMA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gama globulina' FROM analiza_standard WHERE cod_standard='ELECTRO_GAMA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Gamma globulina %' FROM analiza_standard WHERE cod_standard='ELECTRO_GAMA';
INSERT OR IGNORE INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Raport A/G' FROM analiza_standard WHERE cod_standard='ELECTRO_RAPORT';
