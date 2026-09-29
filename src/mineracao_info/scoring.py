from __future__ import annotations

import math
import re
from collections import Counter
from statistics import median
from typing import Any

PT_STOP = {
    "para","como","com","sem","uma","umas","uns","que","por","mais","menos","seu","sua","seus","suas","dos","das","de","do","da","e","ou","em","no","na","nos","nas","um","o","a","os","as","ao","aos","esta","esse","essa","isso","voce","você","agora","hoje","muito","muita","ser","ter","tem","sao","são","foi","vai","ja","já","se","mesmo","quando","onde","porque","pra","pro"
}


def clamp(x: float, lo: float = 0, hi: float = 1) -> float:
    return max(lo, min(hi, x))


def text_signature(text: str) -> str:
    text = re.sub(r"\W+", " ", text.lower()).strip()
    return text[:600]


def top_terms(records: list[dict[str, Any]], n: int = 20) -> list[tuple[str, int]]:
    c = Counter()
    for r in records:
        words = re.findall(r"[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ0-9_-]{3,}", (r.get("text") or "").lower())
        words = [w for w in words if w not in PT_STOP and not w.isdigit()]
        c.update(words)
    return c.most_common(n)


def classify_longevity(days: int | None) -> str:
    if days is None:
        return "sem_data"
    if days <= 7:
        return "teste"
    if days <= 20:
        return "watchlist"
    if days <= 45:
        return "investigar"
    if days <= 90:
        return "forte"
    return "muito_forte"


def compute_score(records: list[dict[str, Any]], sources_requested: list[str], weights: dict[str, int]) -> dict[str, Any]:
    meta = [r for r in records if r["source"] == "meta"]
    n_ads = len(meta)
    advertisers = {r["advertiser"].lower() for r in meta if r.get("advertiser")}
    creatives = {text_signature(r["text"]) for r in meta if r.get("text")}
    days = [r["days_running"] for r in meta if isinstance(r.get("days_running"), int)]
    max_days = max(days) if days else 0
    med_days = median(days) if days else 0
    source_presence = len({r["source"] for r in records if r.get("text") or r.get("raw")})

    volume_norm = clamp(math.log1p(n_ads) / math.log(1001)) if n_ads else 0
    longevity_norm = clamp((0.6 * min(max_days, 120) + 0.4 * min(med_days, 90)) / 108)
    adv_norm = clamp(math.log1p(len(advertisers)) / math.log(31)) if advertisers else 0
    creative_norm = clamp(math.log1p(len(creatives)) / math.log(101)) if creatives else 0
    cross_norm = clamp(source_presence / max(1, len(sources_requested)))

    components = {
        "ad_volume": round(volume_norm * weights.get("ad_volume", 25), 2),
        "longevity": round(longevity_norm * weights.get("longevity", 25), 2),
        "advertiser_diversity": round(adv_norm * weights.get("advertiser_diversity", 20), 2),
        "creative_diversity": round(creative_norm * weights.get("creative_diversity", 15), 2),
        "cross_source_presence": round(cross_norm * weights.get("cross_source_presence", 15), 2),
    }
    return {
        "score": round(sum(components.values()), 1),
        "components": components,
        "meta_ads": n_ads,
        "unique_advertisers": len(advertisers),
        "unique_creatives": len(creatives),
        "max_days": max_days,
        "median_days": med_days,
        "source_presence": source_presence,
    }
