"""SQLite persistence: the Settings blob and the three dashboard caches.

Two independent domains live in the same file, on purpose:
  - settings/teams  -- written only by app.settings_views, read by the
    internal dashboard-fetch endpoints. Never exposed over any API.
  - cache_*         -- the exact JSON payload last shown on each dashboard
    view, written as a side effect of those endpoints, read by
    app.api.external (the static-key REST API) and nowhere else.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, g

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "instance" / "club_dashboard.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    api_token TEXT NOT NULL DEFAULT '',
    event_region TEXT NOT NULL DEFAULT '',
    viqrc_season INTEGER,
    v5rc_season INTEGER
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    number TEXT NOT NULL,
    program TEXT NOT NULL CHECK (program IN ('VIQRC', 'V5RC')),
    grade TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cache_active_teams (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cache_world_skills (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cache_awards (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_CACHE_TABLES = {
    "active_teams": "cache_active_teams",
    "world_skills": "cache_world_skills",
    "awards": "cache_awards",
}


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc: Optional[BaseException] = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(SCHEMA)
    db.execute("INSERT OR IGNORE INTO settings (id, api_token, event_region) VALUES (1, '', '')")
    db.commit()


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()


def get_settings() -> Dict[str, Any]:
    db = get_db()
    row = db.execute(
        "SELECT api_token, event_region, viqrc_season, v5rc_season FROM settings WHERE id = 1"
    ).fetchone()
    team_rows = db.execute(
        "SELECT number, program, grade FROM teams ORDER BY sort_order"
    ).fetchall()
    return {
        "apiToken": row["api_token"] if row else "",
        "eventRegion": row["event_region"] if row else "",
        "viqrcSeason": row["viqrc_season"] if row else None,
        "v5rcSeason": row["v5rc_season"] if row else None,
        "teams": [
            {"number": t["number"], "program": t["program"], "grade": t["grade"]}
            for t in team_rows
        ],
    }


def save_settings(
    api_token: str,
    event_region: str,
    viqrc_season: Optional[int],
    v5rc_season: Optional[int],
    teams: List[Dict[str, str]],
) -> None:
    db = get_db()
    db.execute(
        "UPDATE settings SET api_token = ?, event_region = ?, viqrc_season = ?, v5rc_season = ? WHERE id = 1",
        (api_token, event_region, viqrc_season, v5rc_season),
    )
    db.execute("DELETE FROM teams")
    db.executemany(
        "INSERT INTO teams (number, program, grade, sort_order) VALUES (?, ?, ?, ?)",
        [(t["number"], t["program"], t["grade"], i) for i, t in enumerate(teams)],
    )
    db.commit()


def save_cache(name: str, payload: Dict[str, Any]) -> None:
    table = _CACHE_TABLES[name]
    db = get_db()
    updated_at = datetime.now(timezone.utc).isoformat()
    db.execute(
        f"INSERT INTO {table} (id, payload, updated_at) VALUES (1, ?, ?) "
        f"ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at",
        (json.dumps(payload), updated_at),
    )
    db.commit()


def get_cache(name: str) -> Optional[Dict[str, Any]]:
    table = _CACHE_TABLES[name]
    db = get_db()
    row = db.execute(f"SELECT payload, updated_at FROM {table} WHERE id = 1").fetchone()
    if row is None:
        return None
    return {"payload": json.loads(row["payload"]), "updatedAt": row["updated_at"]}
