from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture
def fixture_loader():
    def load(name: str) -> dict:
        return json.loads((ROOT / "tests" / "fixtures" / name).read_text(encoding="utf-8"))
    return load


@pytest.fixture
def isolated_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "mineracao.db"
    output_path = tmp_path / "outputs"
    monkeypatch.setenv("MINERACAO_DB_PATH", str(db_path))
    monkeypatch.setenv("MINERACAO_OUTPUTS_DIR", str(output_path))
    monkeypatch.delenv("APIFY_API_TOKEN", raising=False)
    return tmp_path

