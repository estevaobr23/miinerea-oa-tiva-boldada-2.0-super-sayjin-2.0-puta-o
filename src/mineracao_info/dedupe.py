from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import NormalizedResult

TRACKING_PARAMS = {"fbclid", "gclid", "ttclid", "utm_campaign", "utm_content", "utm_medium", "utm_source", "utm_term"}


def _canonical_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\W+", " ", text.lower()).strip()


def _canonical_url(value: str | None) -> str:
    if not value:
        return ""
    try:
        parts = urlsplit(value.strip())
        query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS))
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, ""))
    except ValueError:
        return value.strip().lower()


def result_fingerprint(result: NormalizedResult) -> str:
    if result.external_id:
        identity = f"{result.source}|external|{result.external_id.strip().lower()}"
    elif result.landing_url and result.source in {"google", "tiktok"}:
        identity = f"{result.source}|{result.result_type}|url|{_canonical_url(result.landing_url)}"
    else:
        identity = "|".join([
            result.source,
            result.result_type,
            _canonical_text(result.advertiser_id or result.advertiser_name),
            _canonical_url(result.landing_url),
            result.started_at.date().isoformat() if result.started_at else "",
            _canonical_text(" ".join(filter(None, [result.title, result.text, result.description])))[:800],
        ])
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _merge(primary: NormalizedResult, duplicate: NormalizedResult) -> None:
    for name in type(primary).model_fields:
        if name in {"raw_data", "matched_queries", "dedup_key", "query", "keyword"}:
            continue
        current = getattr(primary, name)
        incoming = getattr(duplicate, name)
        if current in (None, "", [], {}) and incoming not in (None, "", [], {}):
            setattr(primary, name, incoming)
    primary.matched_queries = list(dict.fromkeys(primary.matched_queries + duplicate.matched_queries + [duplicate.keyword]))


def deduplicate_results(records: list[NormalizedResult]) -> list[NormalizedResult]:
    unique: dict[str, NormalizedResult] = {}
    for record in records:
        key = result_fingerprint(record)
        record.dedup_key = key
        if key not in unique:
            unique[key] = record.model_copy(deep=True)
        else:
            _merge(unique[key], record)
    return list(unique.values())


def stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
