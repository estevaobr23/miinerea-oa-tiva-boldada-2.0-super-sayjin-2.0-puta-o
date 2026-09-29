from __future__ import annotations

import uuid
from typing import Any

from .config import get_settings, load_yaml
from .skill import load_skill
from .apify_runner import ApifyRunner
from .providers import PROVIDER_CLASSES
from .storage import Storage
from .normalize import normalize_item
from .scoring import compute_score
from .report import build_report

DEPTH_RESULTS = {"quick": 25, "medium": 100, "deep": 300}


def mine(seed: str, depth: str = "quick", sources: list[str] | None = None, country: str = "BR") -> dict[str, Any]:
    sources = sources or ["meta", "tiktok", "google"]
    if depth not in DEPTH_RESULTS:
        raise ValueError(f"depth invalido: {depth}. Use quick, medium ou deep.")
    settings = get_settings(require_token=True)
    skill = load_skill(settings.skill_path, settings.runtime_path)
    provider_cfg = load_yaml(settings.providers_path)
    storage = Storage(settings.db_path)
    runner = ApifyRunner(settings.apify_token)
    run_id = uuid.uuid4().hex[:12]
    storage.create_run(run_id, seed, country, depth, sources, skill.version, skill.sha256)

    records=[]
    provider_stats={}
    max_results=DEPTH_RESULTS[depth]
    error=None
    try:
        for src in sources:
            cfg = provider_cfg.get(src) or {}
            if not cfg.get("enabled", True):
                provider_stats[src] = {"status":"disabled", "count":0, "actor_id":cfg.get("actor_id","")}
                continue
            cls = PROVIDER_CLASSES.get(src)
            if not cls:
                provider_stats[src] = {"status":"unknown_provider", "count":0, "actor_id":cfg.get("actor_id","")}
                continue
            provider = cls(cfg["actor_id"], cfg.get("defaults") or {})
            payload = provider.build_input(seed, max_results, country)
            try:
                _, items = runner.run(provider.actor_id, payload)
                storage.add_items(run_id, src, provider.actor_id, payload, items)
                norm=[normalize_item(src, i) for i in items]
                records.extend(norm)
                provider_stats[src] = {"status":"ok", "count":len(items), "actor_id":provider.actor_id, "input":payload}
            except Exception as exc:
                provider_stats[src] = {"status":"error", "count":0, "actor_id":provider.actor_id, "error":str(exc), "input":payload}

        weights = skill.rules.get("score_weights", {})
        score = compute_score(records, sources, weights)
        report_path = build_report(run_id, seed, country, sources, records, score, skill, provider_stats, settings.outputs_dir)
        storage.finish_run(run_id, str(report_path))
        return {"run_id":run_id, "report_path":str(report_path), "score":score, "providers":provider_stats}
    except Exception as exc:
        error=str(exc)
        storage.finish_run(run_id, "", error=error)
        raise
