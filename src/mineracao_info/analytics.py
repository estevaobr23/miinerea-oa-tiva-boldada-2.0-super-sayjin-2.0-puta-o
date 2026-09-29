from __future__ import annotations

import re
from collections import Counter, defaultdict
from statistics import median
from typing import Any

from .models import NormalizedResult

PT_STOP = {
    "para", "como", "com", "sem", "uma", "umas", "uns", "que", "por", "mais", "menos", "seu", "sua",
    "seus", "suas", "dos", "das", "de", "do", "da", "e", "ou", "em", "no", "na", "nos", "nas", "um",
    "o", "a", "os", "as", "ao", "aos", "esta", "esse", "essa", "isso", "voce", "você", "agora", "hoje",
    "muito", "muita", "ser", "ter", "tem", "sao", "são", "foi", "vai", "ja", "já", "se", "mesmo", "quando",
    "onde", "porque", "pra", "pro", "https", "www", "com.br", "video", "facebook", "instagram", "tiktok",
}

MECHANISM_TERMS = {
    "passo a passo", "protocolo", "método", "metodo", "rotina", "plano", "checklist", "manual", "guia",
    "sistema", "diagnóstico", "diagnostico", "desafio", "cardápio", "cardapio", "lista de compras", "tracker",
    "calculadora", "sem calcular", "pronto para usar", "consulta rápida", "consulta rapida", "ativar", "desligar",
}


def text_signature(value: str | None) -> str:
    return re.sub(r"\W+", " ", (value or "").lower()).strip()[:800]


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


def top_terms(records: list[NormalizedResult], n: int = 25) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for record in records:
        text = " ".join(filter(None, [record.title, record.text, record.description]))
        words = re.findall(r"[a-zA-ZÀ-ÿ][a-zA-ZÀ-ÿ0-9_-]{3,}", text.lower())
        counts.update(word for word in words if word not in PT_STOP and not word.isdigit())
    return counts.most_common(n)


def candidate_mechanisms(records: list[NormalizedResult]) -> list[dict[str, Any]]:
    joined = "\n".join(" ".join(filter(None, [r.title, r.text, r.description])).lower() for r in records)
    candidates = [{"term": term, "occurrences": joined.count(term)} for term in MECHANISM_TERMS if joined.count(term)]
    return sorted(candidates, key=lambda item: (-item["occurrences"], item["term"]))[:15]


def possible_relaunches(records: list[NormalizedResult]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[NormalizedResult]] = defaultdict(list)
    for record in records:
        if record.source != "meta" or not record.advertiser_name or not record.started_at:
            continue
        offer_key = record.domain or " ".join(text_signature(record.text).split()[:8])
        if offer_key:
            groups[(record.advertiser_name.lower(), offer_key)].append(record)
    output: list[dict[str, Any]] = []
    for (advertiser, offer_key), group in groups.items():
        dates = sorted({record.started_at.date().isoformat() for record in group if record.started_at})
        if len(dates) >= 2:
            output.append({
                "advertiser": group[0].advertiser_name,
                "offer_key": offer_key,
                "distinct_start_dates": dates,
                "records": len(group),
                "classification": "possivel_relaunch",
            })
    return sorted(output, key=lambda item: (-len(item["distinct_start_dates"]), item["advertiser"]))[:20]


def build_metrics(records: list[NormalizedResult], raw_count: int) -> dict[str, Any]:
    meta = [record for record in records if record.source == "meta"]
    advertisers = Counter(record.advertiser_name for record in meta if record.advertiser_name)
    copies = {text_signature(record.text) for record in meta if text_signature(record.text)}
    creatives = {record.creative_url or text_signature(record.text) for record in meta if record.creative_url or text_signature(record.text)}
    days = [record.days_running for record in meta if isinstance(record.days_running, int)]
    launches = sorted({record.started_at.date().isoformat() for record in meta if record.started_at})
    domains = Counter(record.domain for record in records if record.domain)
    related = [record.title for record in records if record.result_type == "related_query" and record.title]
    paa = [record.title for record in records if record.result_type == "people_also_ask" and record.title]
    longest = sorted(
        [record for record in meta if isinstance(record.days_running, int)],
        key=lambda record: record.days_running or 0,
        reverse=True,
    )[:20]
    relaunches = possible_relaunches(records)
    return {
        "raw_count": raw_count,
        "deduplicated_count": len(records),
        "source_counts": dict(Counter(record.source for record in records)),
        "top_advertisers": [{"name": name, "count": count} for name, count in advertisers.most_common(20)],
        "independent_advertisers": len(advertisers),
        "distinct_copies": len(copies),
        "distinct_creatives": len(creatives),
        "launch_dates": launches,
        "longevity": {
            "max_days": max(days) if days else 0,
            "median_days": median(days) if days else 0,
            "buckets": dict(Counter(classify_longevity(value) for value in days)),
        },
        "longest_ads": [
            {
                "external_id": record.external_id,
                "advertiser": record.advertiser_name,
                "days_running": record.days_running,
                "started_at": record.started_at.isoformat() if record.started_at else None,
                "ended_at": record.ended_at.isoformat() if record.ended_at else None,
                "is_active": record.is_active,
                "landing_url": record.landing_url,
                "text": (record.text or "")[:300],
            }
            for record in longest
        ],
        "possible_relaunches": relaunches,
        "domains": [{"domain": domain, "count": count} for domain, count in domains.most_common(30)],
        "related_queries": list(dict.fromkeys(related))[:50],
        "people_also_ask": list(dict.fromkeys(paa))[:50],
        "top_terms": [{"term": term, "count": count} for term, count in top_terms(records, 30)],
        "candidate_mechanisms": candidate_mechanisms(records),
    }
