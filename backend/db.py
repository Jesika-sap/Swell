"""Small database layer that runs on SQLite (local development and tests)
or PostgreSQL (production on Render), with the same SQL.

Queries are written with "?" placeholders. For Postgres they are converted
to "%s". Every value is passed as a parameter, never pasted into the SQL
string, which is what prevents SQL injection.
"""
import json
import os
import sqlite3
import threading
import time

import config

_local = threading.local()
_IS_PG = config.DATABASE_URL.startswith(("postgres://", "postgresql://"))


def _connect():
    if _IS_PG:
        import psycopg  # installed on the server from requirements.txt
        from psycopg.rows import dict_row
        return psycopg.connect(config.DATABASE_URL, row_factory=dict_row, autocommit=True)
    conn = sqlite3.connect(config.SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def conn():
    c = getattr(_local, "conn", None)
    if c is None:
        c = _local.conn = _connect()
    return c


def close():
    c = getattr(_local, "conn", None)
    if c is not None:
        c.close()
        _local.conn = None


def _sql(q):
    return q.replace("?", "%s") if _IS_PG else q


def execute(q, params=()):
    c = conn()
    cur = c.execute(_sql(q), params)
    if not _IS_PG:
        c.commit()
    return cur


def query(q, params=()):
    rows = conn().execute(_sql(q), params).fetchall()
    return [dict(r) for r in rows]


def one(q, params=()):
    rows = query(q, params)
    return rows[0] if rows else None


def init():
    path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(path, encoding="utf-8") as f:
        # Drop comments BEFORE splitting on ";" so a semicolon inside a comment
        # can't cut a statement in half (this bug happened twice).
        text = "\n".join(ln.split("--", 1)[0] for ln in f.read().splitlines())
    for s in text.split(";"):
        sql = s.strip()
        if sql:
            execute(sql)
    _migrate()


def _columns(table):
    if _IS_PG:
        return {r["column_name"] for r in query("SELECT column_name FROM information_schema.columns WHERE table_name = ?", (table,))}
    return {r["name"] for r in query(f"PRAGMA table_info({table})")}


def _migrate():
    """Add columns that older databases don't have yet."""
    if "community_id" not in _columns("reports"):
        execute("ALTER TABLE reports ADD COLUMN community_id TEXT")


# ---------- cache helpers ----------

def cache_get(key):
    row = one("SELECT value, expires_at FROM cache WHERE key = ?", (key,))
    if not row or row["expires_at"] < time.time():
        return None
    return json.loads(row["value"])


def cache_set(key, value, ttl):
    expires = time.time() + ttl
    data = json.dumps(value)
    if _IS_PG:
        execute("INSERT INTO cache (key, value, expires_at) VALUES (?, ?, ?) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, expires_at = EXCLUDED.expires_at",
                (key, data, expires))
    else:
        execute("INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)", (key, data, expires))
