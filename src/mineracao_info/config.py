from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv
import yaml

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

# Immutable fuse: even a mistaken YAML edit cannot authorize an unbounded run.
HARD_SAFETY_CEILINGS = {
    "MAX_QUERIES_PER_JOB": 30,
    "MAX_RESULTS_PER_QUERY": 100,
    "MAX_TOTAL_RESULTS_PER_JOB": 1000,
    "MAX_DATASET_ITEMS_PER_RUN": 150,
}

@dataclass(frozen=True)
class Settings:
    base_dir: Path
    apify_token: str
    db_path: Path
    skill_path: Path
    runtime_path: Path
    engine_path: Path
    providers_path: Path
    outputs_dir: Path


def get_settings(require_token: bool = True) -> Settings:
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if require_token and not token:
        raise RuntimeError(
            "APIFY_API_TOKEN nao configurado. Execute configure_token.py ou copie .env.example para .env."
        )
    db_path = BASE_DIR / os.getenv("MINERACAO_DB_PATH", "data/mineracao_info.db")
    skill_path = BASE_DIR / os.getenv(
        "MINERACAO_SKILL_PATH", "skills/SKILL_ATUALIZADA_BIG_NICHOS_LOW_TICKET.md"
    )
    runtime_path = BASE_DIR / os.getenv("MINERACAO_RUNTIME_PATH", "config/skill_runtime.yaml")
    engine_path = BASE_DIR / os.getenv("MINERACAO_ENGINE_PATH", "config/engine.yaml")
    return Settings(
        base_dir=BASE_DIR,
        apify_token=token,
        db_path=db_path,
        skill_path=skill_path,
        runtime_path=runtime_path,
        engine_path=engine_path,
        providers_path=BASE_DIR / "config/providers.yaml",
        outputs_dir=BASE_DIR / os.getenv("MINERACAO_OUTPUTS_DIR", "outputs"),
    )


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_engine_config(settings: Settings | None = None) -> dict:
    settings = settings or get_settings(require_token=False)
    config = load_yaml(settings.engine_path)
    if not config.get("depths") or not config.get("safety"):
        raise RuntimeError(f"Configuracao do engine invalida: {settings.engine_path}")
    safety = config["safety"]
    for name, ceiling in HARD_SAFETY_CEILINGS.items():
        try:
            value = int(safety[name])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Teto de seguranca ausente ou invalido: {name}") from exc
        if value < 1 or value > ceiling:
            raise RuntimeError(f"Teto de seguranca {name} deve estar entre 1 e {ceiling}")
    return config
