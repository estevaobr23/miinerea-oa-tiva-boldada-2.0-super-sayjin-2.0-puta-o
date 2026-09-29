from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from mineracao_info.normalize import normalize_item
from mineracao_info.scoring import compute_score, classify_longevity
from mineracao_info.skill import load_skill


def test_skill_loads():
    s=load_skill(ROOT/"skills/SKILL_ATUALIZADA_BIG_NICHOS_LOW_TICKET.md", ROOT/"config/skill_runtime.yaml")
    assert s.version.startswith("2026")
    assert len(s.sha256)==64


def test_normalize_meta():
    x=normalize_item("meta", {"pageName":"Teste", "body":"Texto de anuncio", "startDate":"2026-07-01", "linkUrl":"https://example.com"})
    assert x["advertiser"]=="Teste"
    assert "Texto" in x["text"]
    assert x["days_running"] is not None


def test_score():
    rec=[{"source":"meta","advertiser":"A","text":"abc mecanismo","days_running":60}, {"source":"meta","advertiser":"B","text":"def mecanismo","days_running":30}, {"source":"tiktok","advertiser":None,"text":"mecanismo","days_running":None}]
    weights={"ad_volume":25,"longevity":25,"advertiser_diversity":20,"creative_diversity":15,"cross_source_presence":15}
    out=compute_score(rec,["meta","tiktok","google"],weights)
    assert 0 <= out["score"] <= 100
    assert classify_longevity(60)=="forte"
