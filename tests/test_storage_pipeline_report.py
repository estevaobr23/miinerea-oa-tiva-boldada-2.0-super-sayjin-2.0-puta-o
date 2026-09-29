from __future__ import annotations

import json
from pathlib import Path

from mineracao_info.models import JobSpec
from mineracao_info.pipeline import run_job
from mineracao_info.storage import Storage


class FakeRunner:
    def __init__(self, fixtures: dict[str, dict], fail_actor: str | None = None):
        self.fixtures = fixtures
        self.fail_actor = fail_actor

    def run(self, actor_id: str, payload: dict, *, dataset_limit: int = 150):
        if actor_id == self.fail_actor:
            raise RuntimeError("falha simulada")
        if "meta" in actor_id:
            item = dict(self.fixtures["meta"])
            item["sourceQuery"] = payload["searchTerms"][0]
            return {"id": "run-meta", "defaultDatasetId": "dataset-meta"}, [item]
        if "tiktok" in actor_id:
            return {"id": "run-tiktok", "defaultDatasetId": "dataset-tiktok"}, [self.fixtures["tiktok"]]
        return {"id": "run-google", "defaultDatasetId": "dataset-google"}, [self.fixtures["google"]]


def test_storage_schema_contains_required_tables(tmp_path: Path):
    storage = Storage(tmp_path / "test.db")
    required = {"jobs", "queries", "raw_results", "normalized_results", "result_queries", "advertisers", "claims", "reports", "scores", "provider_runs", "schema_migrations"}
    assert required <= storage.table_names()


def test_pipeline_generates_packet_and_query_relations(isolated_runtime, fixture_loader):
    fixtures = {name: fixture_loader(f"{name}.json") for name in ("meta", "tiktok", "google")}
    job = JobSpec(seed="Fluxo", depth="quick", sources=["meta"], keywords=["keyword um", "keyword dois"])
    result = run_job(job, runner=FakeRunner(fixtures))
    assert result["status"] == "completed"
    assert result["raw_count"] == 2
    assert result["deduplicated_count"] == 1
    output = Path(result["output_dir"])
    assert {"REPORT.md", "summary.json", "score.json", "normalized.json"} <= {path.name for path in output.iterdir()}
    report = (output / "REPORT.md").read_text(encoding="utf-8")
    assert "RAW COUNT" in report
    assert "DEDUPLICATED COUNT" in report
    assert "MECANISMOS CANDIDATOS" in report
    normalized = json.loads((output / "normalized.json").read_text(encoding="utf-8"))
    assert set(normalized[0]["matched_queries"]) == {"keyword um", "keyword dois"}
    storage = Storage(isolated_runtime / "mineracao.db")
    job_record = storage.get_job(result["job_id"])
    assert job_record["status"] == "completed"
    with storage.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM result_queries").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM claims").fetchone()[0] >= 2


def test_pipeline_marks_partial_when_one_provider_fails(isolated_runtime, fixture_loader):
    fixtures = {name: fixture_loader(f"{name}.json") for name in ("meta", "tiktok", "google")}
    job = JobSpec(seed="Fluxo", sources=["meta", "tiktok"], keywords=["teste"])
    result = run_job(job, runner=FakeRunner(fixtures, fail_actor="clockworks/tiktok-scraper"))
    assert result["status"] == "partial"

