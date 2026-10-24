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
    created_at    TEXT NOT NULL,
    community_id  TEXT               -- the group it was posted to
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

-- Organizations that offer help (food banks, volunteer groups, farm groups...).
-- They stay "not verified" until the app's admin checks them.
CREATE TABLE IF NOT EXISTS orgs (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    about         TEXT,
    services      TEXT NOT NULL,     -- JSON list, e.g. ["volunteers", "food"]
    area          TEXT,              -- e.g. "San Mateo County"
    lat           REAL NOT NULL,
    lon           REAL NOT NULL,
    radius_miles  REAL NOT NULL DEFAULT 25,
    email         TEXT,
    phone         TEXT,
    website       TEXT,
    verified      INTEGER NOT NULL DEFAULT 0,
    example       INTEGER NOT NULL DEFAULT 0,
    key_hash      TEXT NOT NULL,     -- the organization's secret key, stored only as a hash
    created_at    TEXT NOT NULL
);

-- A household asking for help. Organizations nearby that offer that kind of
-- help can see it. Contact details are shown only to the one that accepts it.
CREATE TABLE IF NOT EXISTS help_requests (
    id          TEXT PRIMARY KEY,
    plan_id     TEXT NOT NULL,
    device_id   TEXT NOT NULL,
    need        TEXT NOT NULL,
    details     TEXT,
    contact     TEXT,
    lat         REAL NOT NULL,
    lon         REAL NOT NULL,
    area        TEXT,
    status      TEXT NOT NULL DEFAULT 'open',   -- open, accepted, done, cancelled
    org_id      TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS help_geo ON help_requests (lat, lon);

-- Accounts. A person signs up with a name, email and password. The password is
-- stored only as a salted hash (werkzeug's scrypt), never as plain text.
-- device_id is the account's private key for the app: every phone or browser
-- that logs in uses it, so the account's plans show up everywhere.
CREATE TABLE IF NOT EXISTS accounts (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    pw_hash     TEXT NOT NULL,
    device_id   TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);

-- Communities: a county (San Mateo County) or a city (Millbrae), where only
-- verified officials post updates, and private family or neighborhood groups,
-- joined with an invite code, where every member can post reports.
CREATE TABLE IF NOT EXISTS communities (
    id            TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,      -- county, city, family, neighborhood
    name          TEXT NOT NULL,
    place_key     TEXT UNIQUE,        -- e.g. "county:CA:San Mateo", NULL for groups
    county        TEXT,
    lat           REAL,
    lon           REAL,
    owner_id      TEXT,
    invite_code   TEXT UNIQUE,        -- family and neighborhood groups
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS community_members (
    community_id  TEXT NOT NULL,
    account_id    TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'member',  -- owner, member, official
    safe_at       TEXT,                            -- last "I'm safe" check-in (family groups)
    joined_at     TEXT NOT NULL,
    PRIMARY KEY (community_id, account_id)
);
