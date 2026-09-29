from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ClaimMatch, JobSpec, NormalizedResult

MIGRATIONS: list[tuple[int, str]] = [
    (1, """
    CREATE TABLE IF NOT EXISTS jobs (
      id TEXT PRIMARY KEY,
      seed TEXT NOT NULL,
      depth TEXT NOT NULL,
      country TEXT NOT NULL,
      sources_json TEXT NOT NULL,
      keywords_json TEXT NOT NULL,
      job_json TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('queued','running','partial','completed','failed')),
      raw_count INTEGER NOT NULL DEFAULT 0,
      deduplicated_count INTEGER NOT NULL DEFAULT 0,
      skill_version TEXT,
      skill_sha256 TEXT,
      report_path TEXT,
      output_dir TEXT,
      error TEXT,
      created_at TEXT NOT NULL,
      started_at TEXT,
      finished_at TEXT
    );
    CREATE TABLE IF NOT EXISTS queries (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      source TEXT NOT NULL,
      keyword TEXT NOT NULL,
      status TEXT NOT NULL,
      raw_count INTEGER NOT NULL DEFAULT 0,
      normalized_count INTEGER NOT NULL DEFAULT 0,
      error TEXT,
      created_at TEXT NOT NULL,
      started_at TEXT,
      finished_at TEXT,
      UNIQUE(job_id, source, keyword)
    );
    CREATE TABLE IF NOT EXISTS provider_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      query_id INTEGER REFERENCES queries(id) ON DELETE CASCADE,
      source TEXT NOT NULL,
      actor_id TEXT NOT NULL,
      mode TEXT NOT NULL DEFAULT 'collect',
      apify_run_id TEXT,
      status TEXT NOT NULL,
      input_json TEXT NOT NULL,
      item_count INTEGER NOT NULL DEFAULT 0,
      error TEXT,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS raw_results (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      query_id INTEGER NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
      source TEXT NOT NULL,
      external_id TEXT,
      item_json TEXT NOT NULL,
      inserted_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_raw_results_job_source ON raw_results(job_id, source);
    CREATE TABLE IF NOT EXISTS normalized_results (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      dedup_key TEXT NOT NULL,
      source TEXT NOT NULL,
      external_id TEXT,
      result_type TEXT NOT NULL,
      query_text TEXT NOT NULL,
      keyword TEXT NOT NULL,
      advertiser_name TEXT,
      advertiser_id TEXT,
      title TEXT,
      text TEXT,
      description TEXT,
      landing_url TEXT,
      domain TEXT,
      creative_url TEXT,
      thumbnail_url TEXT,
      started_at TEXT,
      ended_at TEXT,
      is_active INTEGER,
      days_running INTEGER,
      platforms_json TEXT NOT NULL,
      views INTEGER,
      likes INTEGER,
      comments INTEGER,
      shares INTEGER,
      followers INTEGER,
      hashtags_json TEXT NOT NULL,
      music_json TEXT,
      position INTEGER,
      cta TEXT,
      raw_data_json TEXT NOT NULL,
      matched_queries_json TEXT NOT NULL,
      UNIQUE(job_id, dedup_key)
    );
    CREATE INDEX IF NOT EXISTS idx_normalized_job_source ON normalized_results(job_id, source);
    CREATE TABLE IF NOT EXISTS result_queries (
      result_id INTEGER NOT NULL REFERENCES normalized_results(id) ON DELETE CASCADE,
      query_id INTEGER NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
      PRIMARY KEY(result_id, query_id)
    );
    CREATE TABLE IF NOT EXISTS advertisers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      source TEXT NOT NULL,
      advertiser_id TEXT,
      advertiser_name TEXT NOT NULL,
      result_count INTEGER NOT NULL,
      UNIQUE(job_id, source, advertiser_name)
    );
    CREATE TABLE IF NOT EXISTS claims (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      result_id INTEGER REFERENCES normalized_results(id) ON DELETE CASCADE,
      claim_type TEXT NOT NULL,
      matched_term TEXT NOT NULL,
      context TEXT NOT NULL,
      severity TEXT NOT NULL,
      status TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS reports (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      report_path TEXT NOT NULL,
      summary_json TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS scores (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
      score_type TEXT NOT NULL,
      score REAL NOT NULL,
      details_json TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
    """),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


class Storage:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.migrate()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def migrate(self) -> None:
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
            applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
            for version, sql in MIGRATIONS:
                if version in applied:
                    continue
                connection.executescript(sql)
                connection.execute("INSERT INTO schema_migrations(version, applied_at) VALUES(?,?)", (version, _now()))

    def create_job(self, job_id: str, spec: JobSpec, skill_version: str, skill_sha256: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO jobs(id,seed,depth,country,sources_json,keywords_json,job_json,status,skill_version,skill_sha256,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (job_id, spec.seed, spec.depth, spec.country, _json(spec.sources), _json(spec.keywords),
                 spec.model_dump_json(), "queued", skill_version, skill_sha256, _now()),
            )

    def update_job_status(self, job_id: str, status: str, *, error: str | None = None) -> None:
        fields = ["status=?", "error=?"]
        values: list[Any] = [status, error]
        if status == "running":
            fields.append("started_at=?")
            values.append(_now())
        if status in {"partial", "completed", "failed"}:
            fields.append("finished_at=?")
            values.append(_now())
        values.append(job_id)
        with self.connect() as connection:
            connection.execute(f"UPDATE jobs SET {', '.join(fields)} WHERE id=?", values)

    def finish_job(self, job_id: str, status: str, raw_count: int, deduplicated_count: int, report_path: str, output_dir: str, error: str | None = None) -> None:
        with self.connect() as connection:
            connection.execute(
                """UPDATE jobs SET status=?,raw_count=?,deduplicated_count=?,report_path=?,output_dir=?,error=?,finished_at=? WHERE id=?""",
                (status, raw_count, deduplicated_count, report_path, output_dir, error, _now(), job_id),
            )

    def create_query(self, job_id: str, source: str, keyword: str) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO queries(job_id,source,keyword,status,created_at,started_at) VALUES(?,?,?,?,?,?)",
                (job_id, source, keyword, "running", _now(), _now()),
            )
            return int(cursor.lastrowid)

    def finish_query(self, query_id: int, status: str, raw_count: int, normalized_count: int, error: str | None = None) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE queries SET status=?,raw_count=?,normalized_count=?,error=?,finished_at=? WHERE id=?",
                (status, raw_count, normalized_count, error, _now(), query_id),
            )

    def add_provider_run(self, job_id: str, query_id: int, source: str, actor_id: str, mode: str, run: dict[str, Any] | None, payload: dict[str, Any], item_count: int, status: str, error: str | None = None) -> None:
        run = run or {}
        run_id = run.get("id") or run.get("runId")
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO provider_runs(job_id,query_id,source,actor_id,mode,apify_run_id,status,input_json,item_count,error,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (job_id, query_id, source, actor_id, mode, run_id, status, _json(payload), item_count, error, _now()),
            )

    def add_raw_results(self, job_id: str, query_id: int, source: str, items: list[dict[str, Any]]) -> None:
        rows = [(job_id, query_id, source, str(item.get("id") or item.get("adArchiveID") or "") or None, _json(item), _now()) for item in items]
        if not rows:
            return
        with self.connect() as connection:
            connection.executemany(
                "INSERT INTO raw_results(job_id,query_id,source,external_id,item_json,inserted_at) VALUES(?,?,?,?,?,?)",
                rows,
            )

    def persist_results(self, job_id: str, records: list[NormalizedResult], query_ids: dict[tuple[str, str], int]) -> dict[str, int]:
        result_ids: dict[str, int] = {}
        with self.connect() as connection:
            for record in records:
                cursor = connection.execute(
                    """INSERT INTO normalized_results(
                    job_id,dedup_key,source,external_id,result_type,query_text,keyword,advertiser_name,advertiser_id,title,text,description,
                    landing_url,domain,creative_url,thumbnail_url,started_at,ended_at,is_active,days_running,platforms_json,views,likes,
                    comments,shares,followers,hashtags_json,music_json,position,cta,raw_data_json,matched_queries_json)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (job_id, record.dedup_key, record.source, record.external_id, record.result_type, record.query, record.keyword,
                     record.advertiser_name, record.advertiser_id, record.title, record.text, record.description, record.landing_url,
                     record.domain, record.creative_url, record.thumbnail_url, record.started_at.isoformat() if record.started_at else None,
                     record.ended_at.isoformat() if record.ended_at else None, None if record.is_active is None else int(record.is_active),
                     record.days_running, _json(record.platforms), record.views, record.likes, record.comments, record.shares,
                     record.followers, _json(record.hashtags), _json(record.music) if record.music is not None else None,
                     record.position, record.cta, _json(record.raw_data), _json(record.matched_queries)),
                )
                result_id = int(cursor.lastrowid)
                result_ids[record.dedup_key or ""] = result_id
                for keyword in record.matched_queries:
                    query_id = query_ids.get((record.source, keyword))
                    if query_id:
                        connection.execute("INSERT OR IGNORE INTO result_queries(result_id,query_id) VALUES(?,?)", (result_id, query_id))
            advertiser_counts = Counter((record.source, record.advertiser_name, record.advertiser_id) for record in records if record.advertiser_name)
            for (source, name, advertiser_id), count in advertiser_counts.items():
                connection.execute(
                    "INSERT INTO advertisers(job_id,source,advertiser_id,advertiser_name,result_count) VALUES(?,?,?,?,?) ON CONFLICT(job_id,source,advertiser_name) DO UPDATE SET result_count=advertisers.result_count+excluded.result_count, advertiser_id=COALESCE(advertisers.advertiser_id, excluded.advertiser_id)",
                    (job_id, source, advertiser_id, name, count),
                )
        return result_ids

    def persist_claims(self, job_id: str, claims: list[ClaimMatch], result_ids: dict[str, int]) -> None:
        rows = [(job_id, result_ids.get(claim.result_key), claim.claim_type, claim.matched_term, claim.context, claim.severity, claim.status) for claim in claims]
        if rows:
            with self.connect() as connection:
                connection.executemany(
                    "INSERT INTO claims(job_id,result_id,claim_type,matched_term,context,severity,status) VALUES(?,?,?,?,?,?,?)",
                    rows,
                )

    def persist_packet(self, job_id: str, report_path: str, summary: dict[str, Any], score: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO reports(job_id,report_path,summary_json,created_at) VALUES(?,?,?,?)",
                (job_id, report_path, _json(summary), _now()),
            )
            connection.execute(
                "INSERT INTO scores(job_id,score_type,score,details_json,created_at) VALUES(?,?,?,?,?)",
                (job_id, score.get("score_type", "EVIDENCE_SCORE"), float(score.get("score", 0)), _json(score), _now()),
            )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if not row:
                return None
            output = dict(row)
            for key in ("sources_json", "keywords_json", "job_json"):
                output[key.removesuffix("_json")] = json.loads(output.pop(key))
            output["queries"] = [dict(item) for item in connection.execute(
                "SELECT id,source,keyword,status,raw_count,normalized_count,error,started_at,finished_at FROM queries WHERE job_id=? ORDER BY id",
                (job_id,),
            )]
            return output

    def get_report_path(self, job_id: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute("SELECT report_path FROM jobs WHERE id=?", (job_id,)).fetchone()
            return str(row[0]) if row and row[0] else None

    def table_names(self) -> set[str]:
        with self.connect() as connection:
            return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
