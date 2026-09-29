from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  seed TEXT NOT NULL,
  country TEXT NOT NULL,
  depth TEXT NOT NULL,
  sources TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  finished_at TEXT,
  skill_version TEXT,
  skill_sha256 TEXT,
  report_path TEXT,
  error TEXT
);
CREATE TABLE IF NOT EXISTS raw_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  source TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  item_json TEXT NOT NULL,
  inserted_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_run_source ON raw_items(run_id, source);
"""

class Storage:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as con:
            con.executescript(SCHEMA)

    def connect(self):
        return sqlite3.connect(self.path)

    def create_run(self, run_id: str, seed: str, country: str, depth: str, sources: list[str], skill_version: str, skill_sha256: str):
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as con:
            con.execute(
                "INSERT INTO runs(id,seed,country,depth,sources,status,created_at,skill_version,skill_sha256) VALUES(?,?,?,?,?,?,?,?,?)",
                (run_id, seed, country, depth, json.dumps(sources), "running", now, skill_version, skill_sha256),
            )

    def add_items(self, run_id: str, source: str, actor_id: str, payload: dict[str, Any], items: list[dict[str, Any]]):
        now = datetime.now(timezone.utc).isoformat()
        rows = [(run_id, source, actor_id, json.dumps(payload, ensure_ascii=False), json.dumps(i, ensure_ascii=False), now) for i in items]
        with self.connect() as con:
            con.executemany(
                "INSERT INTO raw_items(run_id,source,actor_id,payload_json,item_json,inserted_at) VALUES(?,?,?,?,?,?)",
                rows,
            )

    def finish_run(self, run_id: str, report_path: str, error: str | None = None):
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as con:
            con.execute(
                "UPDATE runs SET status=?, finished_at=?, report_path=?, error=? WHERE id=?",
                ("failed" if error else "done", now, report_path, error, run_id),
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as con:
            con.row_factory = sqlite3.Row
            row = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            return dict(row) if row else None
