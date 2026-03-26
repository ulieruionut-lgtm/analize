-- Job-uri upload PDF asincron: partajate intre toate instanțele/replicile Railway
CREATE TABLE IF NOT EXISTS upload_async_jobs (
  job_id VARCHAR(80) PRIMARY KEY,
  owner_username TEXT NOT NULL DEFAULT '',
  file_name TEXT,
  status VARCHAR(32) NOT NULL DEFAULT 'queued',
  created_at TEXT,
  started_at TEXT,
  finished_at TEXT,
  created_ts DOUBLE PRECISION DEFAULT 0,
  started_ts DOUBLE PRECISION DEFAULT 0,
  finished_ts DOUBLE PRECISION DEFAULT 0,
  response_status INTEGER,
  result_json TEXT
);
