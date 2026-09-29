from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .analytics import build_metrics
from .apify_runner import ApifyRunner
from .claims import detect_claims
from .config import get_settings, load_engine_config, load_yaml
from .dedupe import deduplicate_results
from .models import JobSpec, PipelineResult
from .normalize import normalize_source_item
from .providers import PROVIDER_CLASSES
from .report import build_intelligence_packet
from .scoring import compute_evidence_score
from .skill import load_skill
from .storage import Storage


def _limit_normalized(records: list, source: str, limit: int) -> list:
    """Apply the hard cap while retaining Google's G6 expansion signals."""
    if len(records) <= limit:
        return records
    if source != "google" or limit < 3:
        return records[:limit]

    buckets = (
        [record for record in records if record.result_type == "organic"],
        [record for record in records if record.result_type == "people_also_ask"],
        [record for record in records if record.result_type == "related_query"],
    )
    selected = [bucket[0] for bucket in buckets if bucket]
    selected_ids = {id(record) for record in selected}
    for record in records:
        if len(selected) >= limit:
            break
        if id(record) not in selected_ids:
            selected.append(record)
            selected_ids.add(id(record))
    return selected


def _limits(spec: JobSpec, engine_config: dict[str, Any]) -> dict[str, Any]:
    safety = engine_config["safety"]
    depth = engine_config["depths"].get(spec.depth)
    if not depth:
        raise ValueError(f"depth invalido: {spec.depth}")
    max_queries = min(int(depth["max_queries"]), int(safety["MAX_QUERIES_PER_JOB"]))
    if len(spec.keywords) > max_queries:
        raise ValueError(f"Job possui {len(spec.keywords)} keywords; teto para {spec.depth}: {max_queries}")
    return {
        "max_queries": max_queries,
        "max_results_per_query": min(int(depth["max_results_per_query"]), int(safety["MAX_RESULTS_PER_QUERY"])),
        "max_total_results": min(int(depth["max_total_results"]), int(safety["MAX_TOTAL_RESULTS_PER_JOB"])),
        "max_dataset_items": int(safety["MAX_DATASET_ITEMS_PER_RUN"]),
        "meta_scrape_details": bool(depth.get("meta_scrape_details", False)),
    }


def prepare_job(spec: JobSpec | dict[str, Any], job_id: str | None = None) -> str:
    spec = spec if isinstance(spec, JobSpec) else JobSpec.model_validate(spec)
    settings = get_settings(require_token=False)
    skill = load_skill(settings.skill_path, settings.runtime_path)
    engine_config = load_engine_config(settings)
    _limits(spec, engine_config)
    job_id = job_id or uuid.uuid4().hex[:12]
    Storage(settings.db_path).create_job(job_id, spec, skill.version, skill.sha256)
    return job_id


def run_job(
    spec: JobSpec | dict[str, Any],
    *,
    job_id: str | None = None,
    precreated: bool = False,
    runner: Any | None = None,
) -> dict[str, Any]:
    spec = spec if isinstance(spec, JobSpec) else JobSpec.model_validate(spec)
    settings = get_settings(require_token=runner is None)
    skill = load_skill(settings.skill_path, settings.runtime_path)
    engine_config = load_engine_config(settings)
    limits = _limits(spec, engine_config)
    provider_config = load_yaml(settings.providers_path)
    storage = Storage(settings.db_path)
    job_id = job_id or uuid.uuid4().hex[:12]
    if not precreated:
        storage.create_job(job_id, spec, skill.version, skill.sha256)
    storage.update_job_status(job_id, "running")
    runner = runner or ApifyRunner(settings.apify_token)

    all_records = []
    provider_stats: dict[str, Any] = {}
    query_ids: dict[tuple[str, str], int] = {}
    successful_queries = 0
    failed_queries = 0
    task_count = len(spec.keywords) * len(spec.sources)
    task_index = 0

    try:
        for keyword in spec.keywords:
            for source in spec.sources:
                task_index += 1
                query_id = storage.create_query(job_id, source, keyword)
                query_ids[(source, keyword)] = query_id
                stat_key = f"{source}:{task_index}:{keyword}"
                config = provider_config.get(source) or {}
                actor_id = str(config.get("actor_id") or "")
                stat: dict[str, Any] = {
                    "source": source,
                    "keyword": keyword,
                    "actor_id": actor_id,
                    "status": "running",
                    "items": 0,
                    "normalized": 0,
                }
                provider_stats[stat_key] = stat
                provider_class = PROVIDER_CLASSES.get(source)
                if not provider_class or not actor_id or not config.get("enabled", True):
                    error = "provider desabilitado ou sem configuracao"
                    stat.update(status="failed", error=error)
                    storage.finish_query(query_id, "failed", 0, 0, error)
                    failed_queries += 1
                    continue
                provider = provider_class(actor_id, config.get("defaults") or {})
                remaining_tasks = max(1, task_count - task_index + 1)
                remaining_budget = max(0, limits["max_total_results"] - len(all_records))
                query_limit = min(limits["max_results_per_query"], max(1, remaining_budget // remaining_tasks))
                payload = provider.build_input(
                    keyword,
                    query_limit,
                    spec.country,
                    scrape_details=source == "meta" and limits["meta_scrape_details"],
                )
                try:
                    if spec.preflight and source == "meta":
                        preflight_payload = provider.build_preflight_input(keyword, spec.country)
                        if preflight_payload:
                            try:
                                preflight_run, preflight_items = runner.run(actor_id, preflight_payload, dataset_limit=10)
                                storage.add_provider_run(job_id, query_id, source, actor_id, "preflight", preflight_run, preflight_payload, len(preflight_items), "completed")
                                stat["preflight"] = preflight_items
                            except Exception as exc:
                                storage.add_provider_run(job_id, query_id, source, actor_id, "preflight", None, preflight_payload, 0, "failed", str(exc))
                                stat["preflight_error"] = str(exc)
                    run_info, items = runner.run(actor_id, payload, dataset_limit=limits["max_dataset_items"])
                    storage.add_raw_results(job_id, query_id, source, items)
                    normalized = []
                    for item in items:
                        normalized.extend(normalize_source_item(source, keyword, item))
                    normalized = _limit_normalized(normalized, source, query_limit)
                    all_records.extend(normalized)
                    storage.add_provider_run(job_id, query_id, source, actor_id, "collect", run_info, payload, len(items), "completed")
                    storage.finish_query(query_id, "completed", len(items), len(normalized))
                    stat.update(status="completed", items=len(items), normalized=len(normalized), input=payload)
                    successful_queries += 1
                except Exception as exc:
                    error = str(exc)
                    storage.add_provider_run(job_id, query_id, source, actor_id, "collect", None, payload, 0, "failed", error)
                    storage.finish_query(query_id, "failed", 0, 0, error)
                    stat.update(status="failed", error=error, input=payload)
                    failed_queries += 1

        deduplicated = deduplicate_results(all_records)
        metrics = build_metrics(deduplicated, len(all_records))
        score = compute_evidence_score(deduplicated, metrics, engine_config)
        claims = detect_claims(deduplicated, skill.rules.get("health_claim_flags", []))
        status = "failed" if successful_queries == 0 else "partial" if failed_queries else "completed"
        report_path, summary = build_intelligence_packet(
            job_id=job_id,
            status=status,
            spec=spec,
            records=deduplicated,
            claims=claims,
            score=score,
            metrics=metrics,
            provider_stats=provider_stats,
            skill=skill,
            outputs_dir=settings.outputs_dir,
        )
        result_ids = storage.persist_results(job_id, deduplicated, query_ids)
        storage.persist_claims(job_id, claims, result_ids)
        storage.persist_packet(job_id, str(report_path), summary, score)
        error = "todos os providers falharam" if status == "failed" else None
        storage.finish_job(job_id, status, len(all_records), len(deduplicated), str(report_path), str(report_path.parent), error)
        return PipelineResult(
            job_id=job_id,
            status=status,
            report_path=str(report_path),
            output_dir=str(report_path.parent),
            raw_count=len(all_records),
            deduplicated_count=len(deduplicated),
            score=score,
            providers=provider_stats,
        ).model_dump(mode="json")
    except Exception as exc:
        storage.update_job_status(job_id, "failed", error=str(exc))
        raise


def run_job_file(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    return run_job(JobSpec.from_json_file(path), **kwargs)


def mine(
    seed: str,
    depth: str = "quick",
    sources: list[str] | None = None,
    country: str = "BR",
    keywords: list[str] | None = None,
) -> dict[str, Any]:
    return run_job(JobSpec(seed=seed, depth=depth, sources=sources or ["meta", "tiktok", "google"], country=country, keywords=keywords or []))
