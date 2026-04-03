-- Indexuri suplimentare pentru performanță (migrare 018)
-- Toate cu IF NOT EXISTS — safe de rulat repetat

-- Căutare rapidă după denumire_raw (folosit în backfill + normalizare alias)
CREATE INDEX IF NOT EXISTS idx_rezultate_denumire_raw
    ON rezultate_analize(LOWER(denumire_raw));

-- Filtrare analize necunoscute după aprobată + categorie
CREATE INDEX IF NOT EXISTS idx_analiza_nec_aprobata_cat
    ON analiza_necunoscuta(aprobata, categoria);

-- Polling job-uri async upload
CREATE INDEX IF NOT EXISTS idx_upload_async_status
    ON upload_async_jobs(status);

CREATE INDEX IF NOT EXISTS idx_upload_async_created
    ON upload_async_jobs(created_ts DESC);

-- Căutare pacienți după CNP (case-insensitive)
CREATE INDEX IF NOT EXISTS idx_pacienti_cnp_lower
    ON pacienti(LOWER(cnp));

-- Ordonare buletine per pacient după dată
CREATE INDEX IF NOT EXISTS idx_buletine_pacient_data
    ON buletine(pacient_id, data_buletin DESC);
