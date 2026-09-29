from datetime import datetime, timezone

from mineracao_info.normalize import calculate_longevity, normalize_google, normalize_meta, normalize_tiktok
from mineracao_info.pipeline import _limit_normalized


def test_meta_normalizer_preserves_current_schema(fixture_loader):
    result = normalize_meta("fallback", fixture_loader("meta.json"))[0]
    assert result.external_id == "1234567890123456"
    assert result.keyword == "fallback"
    assert result.query == "emagrecer depois dos 40"
    assert result.advertiser_id == "15087023"
    assert result.title == "Plano guiado"
    assert result.landing_url.startswith("https://example.com")
    assert result.creative_url.startswith("https://www.facebook.com/ads/archive")
    assert result.platforms == ["FACEBOOK", "INSTAGRAM"]
    assert result.is_active is True


def test_tiktok_normalizer_preserves_metrics(fixture_loader):
    result = normalize_tiktok("emagrecimento", fixture_loader("tiktok.json"))[0]
    assert result.external_id == "7234567890123456789"
    assert result.landing_url.endswith("7234567890123456789")
    assert result.views == 125000
    assert result.likes == 12500
    assert result.comments == 340
    assert result.shares == 850
    assert result.followers == 12500
    assert result.hashtags == ["alimentacao", "rotina"]
    assert result.music["musicName"] == "Original Sound"


def test_google_normalizer_expands_serp(fixture_loader):
    results = normalize_google("fallback", fixture_loader("google.json"))
    assert len(results) == 5
    assert [result.result_type for result in results].count("organic") == 2
    assert [result.result_type for result in results].count("people_also_ask") == 1
    assert [result.result_type for result in results].count("related_query") == 2
    assert results[0].domain == "example.org"
    assert results[0].position == 1
    assert all(result.keyword == "fallback" for result in results)
    assert all(result.query == "emagrecimento" for result in results)


def test_google_cap_retains_paa_and_related(fixture_loader):
    item = fixture_loader("google.json")
    item["organicResults"] = item["organicResults"] * 6
    limited = _limit_normalized(normalize_google("emagrecimento", item), "google", 4)
    assert len(limited) == 4
    assert {record.result_type for record in limited} == {"organic", "people_also_ask", "related_query"}


def test_longevity_uses_end_date_for_inactive_ad():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 11, tzinfo=timezone.utc)
    much_later = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert calculate_longevity(start, end, False, now=much_later) == 10
    assert calculate_longevity(start, None, True, now=end) == 10
