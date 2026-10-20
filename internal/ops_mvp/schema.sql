PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS clients (id TEXT PRIMARY KEY, purpose TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sites (id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES clients(id), industry TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cases (
 id TEXT PRIMARY KEY, client_id TEXT NOT NULL REFERENCES clients(id), site_id TEXT NOT NULL REFERENCES sites(id),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL,
 answers TEXT NOT NULL, idempotency_key TEXT NOT NULL, payload_hash TEXT NOT NULL, owner TEXT NOT NULL,
 next_action TEXT NOT NULL, due TEXT NOT NULL, notice TEXT NOT NULL,
 interview TEXT, interview_confirmed INTEGER NOT NULL DEFAULT 0,
 UNIQUE(client_id,idempotency_key)
);
CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), kind TEXT NOT NULL,
 owner TEXT NOT NULL, due TEXT NOT NULL, state TEXT NOT NULL, UNIQUE(case_id,kind));
CREATE TABLE IF NOT EXISTS claims (id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), kind TEXT NOT NULL CHECK(kind IN ('F','T','H','U')), body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), body TEXT NOT NULL, digest TEXT NOT NULL, reviewer TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS modules (case_id TEXT NOT NULL REFERENCES cases(id), code TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(case_id,code));
CREATE TABLE IF NOT EXISTS goals (case_id TEXT NOT NULL REFERENCES cases(id), version INTEGER NOT NULL, body TEXT NOT NULL,
 digest TEXT NOT NULL, lab_approved INTEGER NOT NULL DEFAULT 0, client_approved INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(case_id,version));
CREATE TABLE IF NOT EXISTS experiments (id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), goal_version INTEGER NOT NULL,
 body TEXT NOT NULL, state TEXT NOT NULL, client_approved INTEGER NOT NULL DEFAULT 0, observations TEXT NOT NULL DEFAULT '[]',
 decision TEXT, FOREIGN KEY(case_id,goal_version) REFERENCES goals(case_id,version));
CREATE TABLE IF NOT EXISTS uploads (case_id TEXT NOT NULL REFERENCES cases(id), source_id TEXT NOT NULL, version INTEGER NOT NULL,
 PRIMARY KEY(case_id,source_id,version));
CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), body TEXT NOT NULL,
 fingerprint TEXT NOT NULL, state TEXT NOT NULL, reviewer TEXT, approved_at TEXT);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), occurred_at TEXT NOT NULL,
 action TEXT NOT NULL, actor_id TEXT NOT NULL, actor_role TEXT NOT NULL, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS work_logs (id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), activity TEXT NOT NULL,
 minutes INTEGER NOT NULL, cost TEXT NOT NULL, actor_id TEXT NOT NULL, occurred_at TEXT NOT NULL);
