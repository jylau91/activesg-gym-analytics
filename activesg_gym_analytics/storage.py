from __future__ import annotations

import sqlite3
from pathlib import Path
from .config import DB_PATH
from .scraper import ScrapeResult

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at_utc TEXT NOT NULL,
    fetched_at_sgt TEXT NOT NULL,
    source_url TEXT NOT NULL,
    reader_url TEXT NOT NULL,
    raw_sha256 TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    created_at_utc TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_snapshots_hash_time ON snapshots(raw_sha256, fetched_at_sgt);
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    fetched_at_utc TEXT NOT NULL,
    fetched_at_sgt TEXT NOT NULL,
    gym_name TEXT NOT NULL,
    gym_location TEXT,
    status_text TEXT NOT NULL,
    is_open INTEGER,
    capacity_current INTEGER,
    capacity_total INTEGER,
    occupancy_pct REAL,
    crowd_score REAL,
    source_detail TEXT,
    UNIQUE(snapshot_id, gym_name)
);
CREATE INDEX IF NOT EXISTS idx_observations_time ON observations(fetched_at_sgt);
CREATE INDEX IF NOT EXISTS idx_observations_gym_time ON observations(gym_name, fetched_at_sgt);
"""

def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db(db_path: Path = DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        _migrate_observations(conn)
        conn.commit()

def _migrate_observations(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(observations)")}
    if "gym_location" not in columns:
        conn.execute("ALTER TABLE observations ADD COLUMN gym_location TEXT")

def store_scrape(result: ScrapeResult, db_path: Path = DB_PATH) -> int:
    init_db(db_path)
    with connect(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO snapshots (fetched_at_utc, fetched_at_sgt, source_url, reader_url, raw_sha256, raw_text)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (result.fetched_at_utc, result.fetched_at_sgt, result.source_url, result.reader_url, result.raw_sha256, result.raw_text),
        )
        snapshot_id = int(cur.lastrowid)
        conn.executemany(
            """INSERT OR REPLACE INTO observations (
                snapshot_id, fetched_at_utc, fetched_at_sgt, gym_name, gym_location, status_text, is_open,
                capacity_current, capacity_total, occupancy_pct, crowd_score, source_detail
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(
                snapshot_id, result.fetched_at_utc, result.fetched_at_sgt, obs.gym_name, obs.gym_location, obs.status_text,
                None if obs.is_open is None else int(obs.is_open), obs.capacity_current, obs.capacity_total,
                obs.occupancy_pct, obs.crowd_score, obs.source_detail,
            ) for obs in result.observations],
        )
        conn.commit()
    return snapshot_id

def stats(db_path: Path = DB_PATH) -> dict:
    init_db(db_path)
    with connect(db_path) as conn:
        return {
            "snapshot_count": conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0],
            "observation_count": conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
            "gym_count": conn.execute("SELECT COUNT(DISTINCT gym_name) FROM observations").fetchone()[0],
            "first_fetched_at_sgt": conn.execute("SELECT MIN(fetched_at_sgt) FROM snapshots").fetchone()[0],
            "last_fetched_at_sgt": conn.execute("SELECT MAX(fetched_at_sgt) FROM snapshots").fetchone()[0],
        }
