from __future__ import annotations

import math
from typing import Any

from .analytics import classify_longevity, text_signature, top_terms
from .models import NormalizedResult


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _log_norm(value: int, cap: int) -> float:
    if value <= 0:
        return 0.0
    return _clamp(math.log1p(value) / math.log1p(max(1, cap)))


def compute_evidence_score(records: list[NormalizedResult], metrics: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    score_config = config.get("evidence_score") or {}
    weights = score_config.get("weights") or {}
    caps = score_config.get("reference_caps") or {}
    days = metrics.get("longevity") or {}
    max_days = float(days.get("max_days") or 0)
    median_days = float(days.get("median_days") or 0)
    longevity_norm = _clamp((0.6 * min(max_days, 120) + 0.4 * min(median_days, 90)) / 108)
    sources_present = len({record.source for record in records})
    frequent_terms = [item for item in metrics.get("top_terms", []) if int(item.get("count", 0)) >= 2]
    recurring_frequency = max((int(item["count"]) for item in frequent_terms), default=0)
    components = {
        "deduplicated_volume": _log_norm(len(records), int(caps.get("deduplicated_volume", 200))),
        "longevity": longevity_norm,
        "advertiser_diversity": _log_norm(int(metrics.get("independent_advertisers", 0)), int(caps.get("advertisers", 30))),
        "creative_diversity": _log_norm(int(metrics.get("distinct_creatives", 0)), int(caps.get("creatives", 100))),
        "staggered_start_dates": _log_norm(len(metrics.get("launch_dates", [])), int(caps.get("staggered_dates", 20))),
        "cross_source_presence": _clamp(sources_present / 3),
        "recurring_terms": _log_norm(recurring_frequency, int(caps.get("recurring_term_frequency", 20))),
    }
    points = {name: round(value * float(weights.get(name, 0)), 2) for name, value in components.items()}
    return {
        "score_type": "EVIDENCE_SCORE",
        "score": round(sum(points.values()), 1),
        "components": points,
        "weights": weights,
        "signals": {
            "deduplicated_volume": len(records),
            "max_longevity_days": max_days,
            "median_longevity_days": median_days,
            "independent_advertisers": metrics.get("independent_advertisers", 0),
            "distinct_creatives": metrics.get("distinct_creatives", 0),
            "distinct_start_dates": len(metrics.get("launch_dates", [])),
            "sources_present": sources_present,
            "recurring_terms": len(frequent_terms),
        },
        "interpretation": "Prioriza evidencias coletadas. Nao estima lucro, ROAS, demanda garantida nem recomenda criar uma oferta.",
        "strategic_assessment": None,
    }


def compute_score(records: list[dict[str, Any]], sources_requested: list[str], weights: dict[str, int]) -> dict[str, Any]:
    """Compatibilidade V0.1 para consumidores antigos; não usado pelo pipeline novo."""
    from .analytics import build_metrics
    normalized = [NormalizedResult.model_validate(record) for record in records]
    config = {"evidence_score": {"weights": {
        "deduplicated_volume": weights.get("ad_volume", 25),
        "longevity": weights.get("longevity", 25),
        "advertiser_diversity": weights.get("advertiser_diversity", 20),
        "creative_diversity": weights.get("creative_diversity", 15),
        "staggered_start_dates": 0,
        "cross_source_presence": weights.get("cross_source_presence", 15),
        "recurring_terms": 0,
    }}}
    return compute_evidence_score(normalized, build_metrics(normalized, len(normalized)), config)


__all__ = ["classify_longevity", "compute_evidence_score", "compute_score", "text_signature", "top_terms"]
