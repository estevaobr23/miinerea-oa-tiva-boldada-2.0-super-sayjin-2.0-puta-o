from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urlparse

from .models import NormalizedResult


def _dig(obj: Any, dotted: str) -> Any:
    current = obj
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def first_value(item: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = _dig(item, key)
        if value not in (None, "", [], {}):
            return value
    return None


def parse_date(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    raw = str(value).strip()
    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def calculate_longevity(
    started_at: datetime | None,
    ended_at: datetime | None,
    is_active: bool | None,
    *,
    now: datetime | None = None,
) -> int | None:
    if not started_at:
        return None
    end = (now or datetime.now(timezone.utc)) if is_active is not False else ended_at
    if not end:
        end = ended_at or (now or datetime.now(timezone.utc))
    return max(0, (end - started_at).days)


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _domain(url: Any) -> str | None:
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        host = urlparse(url.strip()).hostname
        return host.lower().removeprefix("www.") if host else None
    except ValueError:
        return None


def _list_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_meta(query: str, item: dict[str, Any]) -> list[NormalizedResult]:
    started = parse_date(first_value(item, ["startDate", "startDateFormatted", "adDeliveryStartTime"]))
    ended = parse_date(first_value(item, ["endDate", "endDateFormatted", "adDeliveryStopTime"]))
    status = first_value(item, ["adStatus", "status"])
    active = first_value(item, ["isActive"])
    if active is None and isinstance(status, str):
        active = status.upper() == "ACTIVE"
    landing = first_value(item, ["ctaUrl", "landingUrl", "landingPageUrl", "destinationUrl", "linkUrl"])
    images = first_value(item, ["imageUrls", "images"])
    videos = first_value(item, ["videoUrls", "videos"])
    thumbnail = first_value(item, ["thumbnailUrl", "pageProfilePictureURL"])
    if not thumbnail and isinstance(images, list) and images:
        thumbnail = images[0]
    creative = first_value(item, ["adSnapshotUrl", "snapshotUrl", "adLibraryURL", "adLibraryUrl"])
    if not creative and isinstance(videos, list) and videos:
        creative = videos[0]
    text = first_value(item, ["adText", "body", "primaryText"])
    if not text:
        bodies = first_value(item, ["adCreativeBodies"])
        if isinstance(bodies, list):
            text = " | ".join(str(value) for value in bodies if value)
    result = NormalizedResult(
        source="meta",
        external_id=str(first_value(item, ["adArchiveID", "adArchiveId", "adId", "archiveId"]) or "") or None,
        query=str(first_value(item, ["sourceQuery", "searchQuery", "query"]) or query),
        keyword=query,
        result_type="ad",
        advertiser_name=first_value(item, ["pageName", "advertiserName", "advertiser"]),
        advertiser_id=str(first_value(item, ["pageID", "pageId", "advertiserPageId"]) or "") or None,
        title=first_value(item, ["ctaHeadline", "headline", "title"]),
        text=str(text) if text is not None else None,
        description=first_value(item, ["ctaDescription", "description"]),
        landing_url=str(landing) if landing else None,
        domain=_domain(landing) or first_value(item, ["ctaDomain"]),
        creative_url=str(creative) if creative else None,
        thumbnail_url=str(thumbnail) if thumbnail else None,
        started_at=started,
        ended_at=ended,
        is_active=bool(active) if active is not None else None,
        platforms=_list_strings(first_value(item, ["publisherPlatforms", "platforms"])),
        followers=_as_int(first_value(item, ["pageInstagramFollowers", "pageFollowers", "pageLikes"])),
        cta=first_value(item, ["ctaText", "ctaType"]),
        raw_data=item,
    )
    result.days_running = calculate_longevity(started, ended, result.is_active)
    return [result]


def normalize_tiktok(query: str, item: dict[str, Any]) -> list[NormalizedResult]:
    author = item.get("authorMeta") if isinstance(item.get("authorMeta"), dict) else {}
    started = parse_date(first_value(item, ["createTimeISO", "createTime", "create_time"]))
    landing = first_value(item, ["webVideoUrl", "webVideoURL", "shareUrl", "url"])
    video_meta = item.get("videoMeta") if isinstance(item.get("videoMeta"), dict) else {}
    thumbnail = first_value(video_meta, ["coverUrl", "originalCoverUrl"])
    hashtag_items = item.get("hashtags") if isinstance(item.get("hashtags"), list) else []
    hashtags: list[str] = []
    for value in hashtag_items:
        tag = value.get("name") or value.get("title") if isinstance(value, dict) else value
        if tag:
            hashtags.append(str(tag).lstrip("#"))
    music = item.get("musicMeta") if isinstance(item.get("musicMeta"), dict) else None
    return [NormalizedResult(
        source="tiktok",
        external_id=str(first_value(item, ["id", "videoId"]) or "") or None,
        query=query,
        keyword=query,
        result_type="video",
        advertiser_name=first_value(author, ["name", "nickName", "nickname"]),
        advertiser_id=str(first_value(author, ["id", "userId"]) or "") or None,
        text=first_value(item, ["text", "caption", "description"]),
        landing_url=str(landing) if landing else None,
        domain=_domain(landing),
        creative_url=str(landing) if landing else first_value(video_meta, ["downloadAddr"]),
        thumbnail_url=str(thumbnail) if thumbnail else None,
        started_at=started,
        is_active=True,
        views=_as_int(item.get("playCount")),
        likes=_as_int(first_value(item, ["diggCount", "likeCount"])),
        comments=_as_int(item.get("commentCount")),
        shares=_as_int(item.get("shareCount")),
        followers=_as_int(first_value(author, ["fans", "followers"])),
        hashtags=list(dict.fromkeys(hashtags)),
        music=music,
        raw_data=item,
    )]


def _google_query(item: dict[str, Any], fallback: str) -> str:
    return str(first_value(item, ["searchQuery.term", "searchQueryTerm", "query"]) or fallback)


def normalize_google(query: str, item: dict[str, Any]) -> list[NormalizedResult]:
    actual_query = _google_query(item, query)
    records: list[NormalizedResult] = []
    organic = item.get("organicResults") if isinstance(item.get("organicResults"), list) else []
    for index, value in enumerate(organic, start=1):
        if not isinstance(value, dict):
            continue
        url = first_value(value, ["url", "link"])
        records.append(NormalizedResult(
            source="google", query=actual_query, keyword=query, result_type="organic",
            title=first_value(value, ["title"]), text=first_value(value, ["description", "snippet"]),
            description=first_value(value, ["description", "snippet"]), landing_url=str(url) if url else None,
            domain=_domain(url), position=_as_int(value.get("position")) or index, raw_data=value,
        ))
    paa = item.get("peopleAlsoAsk") if isinstance(item.get("peopleAlsoAsk"), list) else []
    for index, value in enumerate(paa, start=1):
        if not isinstance(value, dict):
            continue
        url = first_value(value, ["url", "link"])
        answer = first_value(value, ["answer", "answerSnippet", "snippet"])
        records.append(NormalizedResult(
            source="google", query=actual_query, keyword=query, result_type="people_also_ask",
            title=first_value(value, ["question", "title"]), text=answer, description=answer,
            landing_url=str(url) if url else None, domain=_domain(url), position=index, raw_data=value,
        ))
    related_values: list[Any] = []
    for key in ("relatedQueries", "relatedSearches"):
        value = item.get(key)
        if isinstance(value, list):
            related_values.extend(value)
    for index, value in enumerate(related_values, start=1):
        if isinstance(value, dict):
            title = first_value(value, ["title", "query", "text"])
            url = first_value(value, ["url", "link"])
            raw = value
        else:
            title, url, raw = str(value), None, {"value": value}
        if title:
            records.append(NormalizedResult(
                source="google", query=actual_query, keyword=query, result_type="related_query",
                title=str(title), text=str(title), landing_url=str(url) if url else None,
                domain=_domain(url), position=index, raw_data=raw,
            ))
    return records


def normalize_source_item(source: str, query: str, item: dict[str, Any]) -> list[NormalizedResult]:
    if source == "meta":
        return normalize_meta(query, item)
    if source == "tiktok":
        return normalize_tiktok(query, item)
    if source == "google":
        return normalize_google(query, item)
    raise ValueError(f"Fonte nao suportada: {source}")


def normalize_item(source: str, item: dict[str, Any], query: str = "unknown") -> dict[str, Any]:
    """Compatibilidade V0.1; novos fluxos usam normalize_source_item."""
    records = normalize_source_item(source, query, item)
    return records[0].model_dump(mode="json") if records else {}
