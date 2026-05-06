-- Migrare 021: Aliases TEO HEALTH / Spitalul Sf. Constantin Brasov
-- Acoperă format buletin tabelar cu coloane Nr|Denumire|Rezultat|UM|Interval

-- ─── Standarde noi ────────────────────────────────────────────────────────────
INSERT INTO analiza_standard (cod_standard, denumire_standard) VALUES
('CALCIU_URINA',    'Calciu urinar'),
('UROCULTURA',      'Urocultura (examen bacteriologic urinar)'),
('SEDIMENT_URINA',  'Sediment urinar (examen microscopic)')
ON CONFLICT (cod_standard) DO NOTHING;

-- ─── eGFR (Valoare eGFR) ──────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Valoare eGFR' FROM analiza_standard WHERE cod_standard='EGFR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Valoare eGFR:' FROM analiza_standard WHERE cod_standard='EGFR' ON CONFLICT (alias) DO NOTHING;

-- ─── Calciu ionic (= Calciu seric pentru tracking) ───────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Calciu ionic seric' FROM analiza_standard WHERE cod_standard='CALCIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Calciu ionic' FROM analiza_standard WHERE cod_standard='CALCIU' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Ca ionic' FROM analiza_standard WHERE cod_standard='CALCIU' ON CONFLICT (alias) DO NOTHING;

-- ─── Calciu urinar ────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Calciu urinar' FROM analiza_standard WHERE cod_standard='CALCIU_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Calciu urinar:' FROM analiza_standard WHERE cod_standard='CALCIU_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '* Calciu urinar' FROM analiza_standard WHERE cod_standard='CALCIU_URINA' ON CONFLICT (alias) DO NOTHING;

-- ─── Urocultura ───────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Urocultura' FROM analiza_standard WHERE cod_standard='UROCULTURA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Urocultură' FROM analiza_standard WHERE cod_standard='UROCULTURA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Examen bacteriologic urinar' FROM analiza_standard WHERE cod_standard='UROCULTURA' ON CONFLICT (alias) DO NOTHING;

-- ─── Examen exudat faringian ──────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Examen din exudat faringian' FROM analiza_standard WHERE cod_standard='MICRO_EXAM_MIC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Examen exudat faringian' FROM analiza_standard WHERE cod_standard='MICRO_EXAM_MIC' ON CONFLICT (alias) DO NOTHING;

-- ─── Hemoleucograma: numar absolut (Numar X format TEO HEALTH) ───────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar neutrofile' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numarul neutrofilelor' FROM analiza_standard WHERE cod_standard='NEUTROFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar limfocite' FROM analiza_standard WHERE cod_standard='LIMFOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar monocite' FROM analiza_standard WHERE cod_standard='MONOCITE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar eozinofile' FROM analiza_standard WHERE cod_standard='EOZINOFILE_NR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Numar bazofile' FROM analiza_standard WHERE cod_standard='BAZOFILE_NR' ON CONFLICT (alias) DO NOTHING;

-- ─── Hemoleucograma: procente fara spatiu (Limfocite% format TEO HEALTH) ──────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Neutrofile%' FROM analiza_standard WHERE cod_standard='NEUTROFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Limfocite%' FROM analiza_standard WHERE cod_standard='LIMFOCITE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Monocite%' FROM analiza_standard WHERE cod_standard='MONOCITE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Eozinofile%' FROM analiza_standard WHERE cod_standard='EOZINOFILE_PCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Bazofile%' FROM analiza_standard WHERE cod_standard='BAZOFILE_PCT' ON CONFLICT (alias) DO NOTHING;

-- ─── HCT% si RDW% (cu % lipit de nume) ───────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HCT%' FROM analiza_standard WHERE cod_standard='HCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HCT% (Hematocrit)' FROM analiza_standard WHERE cod_standard='HCT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RDW%' FROM analiza_standard WHERE cod_standard='RDW' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RDW% (Largimea distributiei eritrocitare)' FROM analiza_standard WHERE cod_standard='RDW' ON CONFLICT (alias) DO NOTHING;

-- ─── TGO / TGP (format TEO HEALTH cu slash si linie) ─────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGO / AST - ASPARTATAMINOTRANSFERAZA' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGO/AST-ASPARTATAMINOTRANSFERAZA' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ASPARTATAMINOTRANSFERAZA' FROM analiza_standard WHERE cod_standard='AST' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGP / ALT - ALANINAMINOTRANSFERAZA' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'TGP/ALT-ALANINAMINOTRANSFERAZA' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'ALANINAMINOTRANSFERAZA' FROM analiza_standard WHERE cod_standard='ALT' ON CONFLICT (alias) DO NOTHING;

-- ─── Uree Nitrogen ────────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Uree Nitrogen' FROM analiza_standard WHERE cod_standard='UREE' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Uree Nitrogen (BUN)' FROM analiza_standard WHERE cod_standard='UREE' ON CONFLICT (alias) DO NOTHING;

-- ─── PCR / CRP (format cu prefix PCR) ────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PCR' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PCR - Proteina C reactiva' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PCR - Proteina C reactivă' FROM analiza_standard WHERE cod_standard='CRP' ON CONFLICT (alias) DO NOTHING;

-- ─── Factor Reumatoid (forma fara paranteze, dupa _fara_paranteze) ────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Factor Reumatoid' FROM analiza_standard WHERE cod_standard='FR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Factor reumatoid' FROM analiza_standard WHERE cod_standard='FR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Factor Reumatoid (FR - cantitativ)' FROM analiza_standard WHERE cod_standard='FR' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FR cantitativ' FROM analiza_standard WHERE cod_standard='FR' ON CONFLICT (alias) DO NOTHING;

-- ─── Magneziu seric (forma lunga explicita) ───────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Magneziu seric' FROM analiza_standard WHERE cod_standard='MAGNEZIU' ON CONFLICT (alias) DO NOTHING;

-- ─── Creatinina urinara + Microalbumina ───────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina urinara' FROM analiza_standard WHERE cod_standard='CREAT_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina urinară' FROM analiza_standard WHERE cod_standard='CREAT_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '* Creatinina urinara' FROM analiza_standard WHERE cod_standard='CREAT_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Microalbumina' FROM analiza_standard WHERE cod_standard='MICROALBUMIN' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '* Microalbumina' FROM analiza_standard WHERE cod_standard='MICROALBUMIN' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Microalbuminurie' FROM analiza_standard WHERE cod_standard='MICROALBUMIN' ON CONFLICT (alias) DO NOTHING;

-- ─── Glicemie (forma lunga cu paranteze) ─────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glicemie (glucoza serica)' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Glicemie (glucoză serică)' FROM analiza_standard WHERE cod_standard='GLUCOZA_FASTING' ON CONFLICT (alias) DO NOTHING;

-- ─── Creatinina serica (forma cu paranteze) ───────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina (serica)' FROM analiza_standard WHERE cod_standard='CREATININA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Creatinina (serică)' FROM analiza_standard WHERE cod_standard='CREATININA' ON CONFLICT (alias) DO NOTHING;

-- ─── RBC / HGB cu forma lunga in paranteze ───────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RBC (Numar eritrocite)' FROM analiza_standard WHERE cod_standard='RBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'HGB (Hemoglobina)' FROM analiza_standard WHERE cod_standard='HB' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'WBC (Numar leucocite)' FROM analiza_standard WHERE cod_standard='WBC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'PLT (Numar trombocite)' FROM analiza_standard WHERE cod_standard='PLT' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MPV (Volumul trombocitar mediu)' FROM analiza_standard WHERE cod_standard='MPV' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MCV (Volum eritrocitar mediu)' FROM analiza_standard WHERE cod_standard='MCV' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MCH (Hemoglobina eritrocitara medie)' FROM analiza_standard WHERE cod_standard='MCH' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'MCHC (Concentratia eritrocitara medie de hemoglobina)' FROM analiza_standard WHERE cod_standard='MCHC' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'RDW% (Largimea distributiei eritrocitare)' FROM analiza_standard WHERE cod_standard='RDW' ON CONFLICT (alias) DO NOTHING;

-- ─── FT4 forma TEO HEALTH ─────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FT4 - Tiroxina libera' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'FT4 - Tiroxină liberă' FROM analiza_standard WHERE cod_standard='FT4' ON CONFLICT (alias) DO NOTHING;

-- ─── Sediment urinar ──────────────────────────────────────────────────────────
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Sediment urinar' FROM analiza_standard WHERE cod_standard='SEDIMENT_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, '* Sediment urinar' FROM analiza_standard WHERE cod_standard='SEDIMENT_URINA' ON CONFLICT (alias) DO NOTHING;
INSERT INTO analiza_alias (analiza_standard_id, alias) SELECT id, 'Examen sediment urinar' FROM analiza_standard WHERE cod_standard='SEDIMENT_URINA' ON CONFLICT (alias) DO NOTHING;
