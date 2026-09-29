from pathlib import Path
from dataclasses import replace

import pytest
from pydantic import ValidationError

from mineracao_info.config import get_settings, load_engine_config
from mineracao_info.models import JobSpec
from mineracao_info.pipeline import _limits
from mineracao_info.skill import load_skill


ROOT = Path(__file__).resolve().parents[1]


def test_skill_loads_with_hash():
    skill = load_skill(ROOT / "skills/SKILL_ATUALIZADA_BIG_NICHOS_LOW_TICKET.md", ROOT / "config/skill_runtime.yaml")
    assert skill.version == "2026-09-28-big-nichos-low-ticket"
    assert len(skill.sha256) == 64


def test_job_parsing_and_default_query(tmp_path: Path):
    path = tmp_path / "job.json"
    path.write_text('{"seed":"MeuFluxo","depth":"quick","country":"br","sources":["meta"]}', encoding="utf-8")
    job = JobSpec.from_json_file(path)
    assert job.country == "BR"
    assert job.keywords == ["MeuFluxo"]


def test_job_deduplicates_keywords_and_sources():
    job = JobSpec(seed="teste", sources=["meta", "meta"], keywords=[" a  b ", "a b"])
    assert job.sources == ["meta"]
    assert job.keywords == ["a b"]


def test_engine_config_has_rigid_caps():
    config = load_engine_config(get_settings(require_token=False))
    assert config["safety"]["MAX_QUERIES_PER_JOB"] == 30
    assert config["depths"]["quick"]["max_results_per_query"] < config["depths"]["deep"]["max_results_per_query"]
    job = JobSpec(seed="x1", keywords=[f"k{i}" for i in range(6)])
    with pytest.raises(ValueError, match="teto"):
        _limits(job, config)


def test_engine_config_rejects_ceiling_increase(tmp_path: Path):
    settings = get_settings(require_token=False)
    unsafe = tmp_path / "engine.yaml"
    unsafe.write_text(
        settings.engine_path.read_text(encoding="utf-8").replace("MAX_QUERIES_PER_JOB: 30", "MAX_QUERIES_PER_JOB: 300"),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="MAX_QUERIES_PER_JOB"):
        load_engine_config(replace(settings, engine_path=unsafe))


def test_invalid_source_is_rejected():
    with pytest.raises(ValidationError):
        JobSpec(seed="teste", sources=["invalid"])
