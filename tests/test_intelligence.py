from mineracao_info.analytics import build_metrics, classify_longevity
from mineracao_info.claims import detect_claims
from mineracao_info.config import get_settings, load_engine_config
from mineracao_info.dedupe import deduplicate_results
from mineracao_info.normalize import normalize_google, normalize_meta
from mineracao_info.scoring import compute_evidence_score


def test_dedup_preserves_all_query_provenance(fixture_loader):
    item = fixture_loader("meta.json")
    first = normalize_meta("keyword um", item)[0]
    second = normalize_meta("keyword dois", item)[0]
    unique = deduplicate_results([first, second])
    assert len(unique) == 1
    assert unique[0].matched_queries == ["keyword um", "keyword dois"]


def test_url_fingerprint_removes_tracking_parameters(fixture_loader):
    item = fixture_loader("google.json")
    first = normalize_google("um", item)[0]
    second = first.model_copy(deep=True)
    second.keyword = "dois"
    second.matched_queries = ["dois"]
    second.landing_url = "https://example.org/plano?utm_source=outra"
    unique = deduplicate_results([first, second])
    assert len(unique) == 1
    assert set(unique[0].matched_queries) == {"um", "dois"}


def test_claims_are_contextual_records(fixture_loader):
    records = deduplicate_results(normalize_meta("teste", fixture_loader("meta.json")))
    claims = detect_claims(records)
    terms = {claim.matched_term.lower() for claim in claims}
    assert "reversão" in terms
    assert "sem dieta" in terms
    assert any("7 dias" in term for term in terms)
    assert all(claim.result_key == records[0].dedup_key for claim in claims)
    assert all(claim.status in {"CLAIM_ENCONTRADO", "VALIDAR_TECNICAMENTE"} for claim in claims)


def test_evidence_score_is_bounded_and_not_strategic(fixture_loader):
    records = deduplicate_results(normalize_meta("teste", fixture_loader("meta.json")) + normalize_google("teste", fixture_loader("google.json")))
    metrics = build_metrics(records, raw_count=6)
    score = compute_evidence_score(records, metrics, load_engine_config(get_settings(require_token=False)))
    assert 0 <= score["score"] <= 100
    assert score["score_type"] == "EVIDENCE_SCORE"
    assert score["strategic_assessment"] is None
    assert sum(score["weights"].values()) == 100
    assert classify_longevity(60) == "forte"

