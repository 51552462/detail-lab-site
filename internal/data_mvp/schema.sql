PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS tenant (client_id TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS sites (site_id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES tenant(client_id));
CREATE TABLE IF NOT EXISTS metrics (
  site_id TEXT NOT NULL REFERENCES sites(site_id), metric_id TEXT NOT NULL,
  definition_version TEXT NOT NULL, unit TEXT NOT NULL, definition TEXT NOT NULL,
  PRIMARY KEY(site_id, metric_id, definition_version)
);
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT NOT NULL, version INTEGER NOT NULL, sha256 TEXT NOT NULL,
  collected_at TEXT NOT NULL, origin TEXT NOT NULL, period_start TEXT NOT NULL, period_end TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN ('pending','approved','rejected')),
  reviewer TEXT, reviewed_at TEXT, PRIMARY KEY(source_id,version)
);
CREATE TABLE IF NOT EXISTS observations (
  source_id TEXT NOT NULL, version INTEGER NOT NULL, row_key TEXT NOT NULL,
  site_id TEXT NOT NULL, metric_id TEXT NOT NULL, definition_version TEXT NOT NULL,
  observed_on TEXT NOT NULL, value TEXT NOT NULL,
  PRIMARY KEY(source_id,version,row_key),
  UNIQUE(source_id,version,site_id,metric_id,definition_version,observed_on),
  FOREIGN KEY(source_id,version) REFERENCES sources(source_id,version),
  FOREIGN KEY(site_id,metric_id,definition_version) REFERENCES metrics(site_id,metric_id,definition_version)
);
CREATE TABLE IF NOT EXISTS report_runs (
  report_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, source_version INTEGER NOT NULL,
  created_at TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'draft',
  FOREIGN KEY(source_id,source_version) REFERENCES sources(source_id,version)
);
CREATE TABLE IF NOT EXISTS audit (
  event_id INTEGER PRIMARY KEY, occurred_at TEXT NOT NULL, action TEXT NOT NULL,
  reference_id TEXT NOT NULL, actor_role TEXT NOT NULL
);
