from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterable

TEXT_KEYS = ["body", "text", "adText", "primaryText", "caption", "description", "title", "headline", "name"]
ADVERTISER_KEYS = ["pageName", "advertiserName", "page_name", "advertiser", "authorMeta.name", "authorMeta.nickname", "author"]
START_KEYS = ["startDate", "start_date", "adDeliveryStartTime", "ad_delivery_start_time", "startDateFormatted", "dateStarted"]
URL_KEYS = ["linkUrl", "landingPageUrl", "destinationUrl", "url", "webUrl", "shareUrl"]


def _dig(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def first_value(item: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        v = _dig(item, key)
        if v not in (None, "", [], {}):
            return v
    return None


def flatten_text(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in TEXT_KEYS:
        v = first_value(item, [key])
        if isinstance(v, str):
            parts.append(v)
    if not parts:
        # fallback controlado: apenas strings curtas do primeiro nivel
        for v in item.values():
            if isinstance(v, str) and 3 <= len(v) <= 2000:
                parts.append(v)
    seen = set()
    out = []
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip()
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return " | ".join(out)


def parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        # epoch seconds or ms
        x = float(value)
        if x > 10_000_000_000:
            x /= 1000
        try:
            return datetime.fromtimestamp(x, tz=timezone.utc)
        except Exception:
            return None
    s = str(value).strip()
    for candidate in (s, s.replace("Z", "+00:00")):
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def normalize_item(source: str, item: dict[str, Any]) -> dict[str, Any]:
    start = parse_date(first_value(item, START_KEYS))
    now = datetime.now(timezone.utc)
    days = max(0, (now - start).days) if start else None
    advertiser = first_value(item, ADVERTISER_KEYS)
    if isinstance(advertiser, dict):
        advertiser = advertiser.get("name") or advertiser.get("nickname")
    return {
        "source": source,
        "text": flatten_text(item),
        "advertiser": str(advertiser).strip() if advertiser else None,
        "start_date": start.isoformat() if start else None,
        "days_running": days,
        "url": first_value(item, URL_KEYS),
        "raw": item,
    }
