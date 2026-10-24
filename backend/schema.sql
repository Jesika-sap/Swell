-- Database schema. Works on both SQLite (local) and PostgreSQL (production).
-- Times are stored as ISO-8601 text in UTC so both databases sort them the same way.

-- A household's saved plan. No names or accounts: a plan belongs to an
-- anonymous device id the app creates on first launch.
CREATE TABLE IF NOT EXISTS plans (
    id            TEXT PRIMARY KEY,
    device_id     TEXT NOT NULL,
    label         TEXT,              -- e.g. "Home" or "Grandma's house"
    address       TEXT,
    lat           REAL NOT NULL,
    lon           REAL NOT NULL,
    county        TEXT,
    city          TEXT,
    state         TEXT,
    language      TEXT NOT NULL DEFAULT 'en',
    household     TEXT NOT NULL,     -- JSON: kids, older adults, pets, disability, car, renter...
    risk          TEXT NOT NULL,     -- JSON: level, score, factors
    checklist     TEXT NOT NULL,     -- JSON list of tasks
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS plans_device ON plans (device_id);

-- Which checklist tasks are done. One row per plan + task.
CREATE TABLE IF NOT EXISTS checklist_done (
    plan_id   TEXT NOT NULL,
    item_id   TEXT NOT NULL,
    done_at   TEXT NOT NULL,
    PRIMARY KEY (plan_id, item_id)
);

-- Neighbors' reports of flooding, clogged drains, landslides, downed trees.
CREATE TABLE IF NOT EXISTS reports (
    id            TEXT PRIMARY KEY,
    device_id     TEXT NOT NULL,
    kind          TEXT NOT NULL,     -- flooding, drain, landslide, tree, power, road, other
    title         TEXT NOT NULL,
    note          TEXT,
    severity      INTEGER NOT NULL,  -- 1 (minor) to 3 (dangerous)
    lat           REAL NOT NULL,
    lon           REAL NOT NULL,
    county        TEXT,
    photo         TEXT,              -- compressed JPEG as a data URL, or NULL
    ai_checked    INTEGER NOT NULL DEFAULT 0,
    confirmations INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'open',  -- open, cleared
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS reports_geo ON reports (lat, lon);

-- One "I see this too" per device per report, so counts can't be inflated.
CREATE TABLE IF NOT EXISTS report_confirms (
    report_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    PRIMARY KEY (report_id, device_id)
);

-- Saved answers from outside services (weather alerts, flood zones, AI news)
-- so we stay inside their rate limits and the app stays fast.
CREATE TABLE IF NOT EXISTS cache (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    expires_at REAL NOT NULL
);
