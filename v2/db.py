"""SQLite storage. Run the CLIs from anywhere; relative DB paths use the repo root."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY, kind TEXT, source TEXT, brand TEXT, title TEXT,
    url TEXT, image_url TEXT, image_urls TEXT, category TEXT, tags TEXT,
    price TEXT, currency TEXT, condition TEXT, sizes TEXT, available INTEGER,
    first_seen_at TEXT, last_seen_at TEXT, last_checked_at TEXT
);
CREATE TABLE IF NOT EXISTS rejections (
    source TEXT, external_id TEXT, title TEXT, reason TEXT, seen_at TEXT,
    PRIMARY KEY (source, external_id)
);
CREATE TABLE IF NOT EXISTS fetch_runs (
    id INTEGER PRIMARY KEY, source TEXT, started_at TEXT, finished_at TEXT,
    ok INTEGER, pages INTEGER, items_seen INTEGER, error TEXT
);
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY, name TEXT, token TEXT UNIQUE, created_at TEXT
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY, person_id INTEGER REFERENCES people(id),
    item_id TEXT REFERENCES items(id),
    reaction TEXT CHECK (reaction IN ('dislike', 'like', 'love')),
    note TEXT, created_at TEXT, updated_at TEXT, UNIQUE (person_id, item_id)
);
CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY, person_id INTEGER REFERENCES people(id),
    created_at TEXT, model TEXT, prompt_version TEXT, feedback_ids TEXT,
    prompt_json TEXT, result_json TEXT, edited_text TEXT,
    input_tokens INTEGER, output_tokens INTEGER, cache_hit_tokens INTEGER,
    cost_usd REAL, latency_ms INTEGER, error TEXT
);
"""


def now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    path = Path(os.environ.get('CLOTHESREC_DB', 'data/clothesrec.db'))
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript(SCHEMA)
    return conn


def upsert_item(conn, item):
    columns = list(item)
    updates = ', '.join(f'{key}=excluded.{key}' for key in columns
                        if key not in ('id', 'first_seen_at'))
    conn.execute(f"INSERT INTO items ({', '.join(columns)}) "
                 f"VALUES ({', '.join('?' for _ in columns)}) "
                 f"ON CONFLICT(id) DO UPDATE SET {updates}",
                 [item[key] for key in columns])


def display_item(row):
    item = dict(row)
    for key in ('image_urls', 'tags', 'sizes'):
        item[key] = json.loads(item[key] or '[]')
    return item


def set_feedback(conn, person_id, item_id, reaction, note):
    timestamp = now()
    conn.execute('''INSERT INTO feedback
        (person_id, item_id, reaction, note, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(person_id, item_id) DO UPDATE SET
        reaction=excluded.reaction, note=excluded.note, updated_at=excluded.updated_at''',
        (person_id, item_id, reaction, note, timestamp, timestamp))
    return dict(conn.execute('''SELECT id, reaction, note, updated_at FROM feedback
        WHERE person_id=? AND item_id=?''', (person_id, item_id)).fetchone())


def clear_feedback(conn, person_id, item_id):
    conn.execute('DELETE FROM feedback WHERE person_id=? AND item_id=?',
                 (person_id, item_id))
