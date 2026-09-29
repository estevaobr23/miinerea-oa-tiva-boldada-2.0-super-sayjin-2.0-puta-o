from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Source = Literal["meta", "tiktok", "google"]
Depth = Literal["quick", "medium", "deep"]
JobStatus = Literal["queued", "running", "partial", "completed", "failed"]


class JobSpec(BaseModel):
    seed: str = Field(min_length=2, max_length=300)
    depth: Depth = "quick"
    country: str = Field(default="BR", min_length=2, max_length=3)
    sources: list[Source] = Field(default_factory=lambda: ["meta", "tiktok", "google"])
    keywords: list[str] = Field(default_factory=list)
    preflight: bool = False

    @field_validator("seed")
    @classmethod
    def clean_seed(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("sources")
    @classmethod
    def unique_sources(cls, value: list[Source]) -> list[Source]:
        if not value:
            raise ValueError("sources nao pode ser vazio")
        return list(dict.fromkeys(value))

    @field_validator("keywords")
    @classmethod
    def clean_keywords(cls, value: list[str]) -> list[str]:
        cleaned = [" ".join(str(item).split()) for item in value]
        cleaned = [item for item in cleaned if item]
        return list(dict.fromkeys(cleaned))

    @model_validator(mode="after")
    def ensure_queries(self) -> "JobSpec":
        if not self.keywords:
            self.keywords = [self.seed]
        return self

    @classmethod
    def from_json_file(cls, path: str | Path) -> "JobSpec":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))


class NormalizedResult(BaseModel):
    source: Source
    external_id: str | None = None
    query: str
    keyword: str
    result_type: str = "result"
    advertiser_name: str | None = None
    advertiser_id: str | None = None
    title: str | None = None
    text: str | None = None
    description: str | None = None
    landing_url: str | None = None
    domain: str | None = None
    creative_url: str | None = None
    thumbnail_url: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    is_active: bool | None = None
    platforms: list[str] = Field(default_factory=list)
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    followers: int | None = None
    hashtags: list[str] = Field(default_factory=list)
    music: dict[str, Any] | str | None = None
    position: int | None = None
    cta: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    matched_queries: list[str] = Field(default_factory=list)
    dedup_key: str | None = None
    days_running: int | None = None

    @model_validator(mode="after")
    def set_query_provenance(self) -> "NormalizedResult":
        if not self.matched_queries:
            self.matched_queries = [self.keyword]
        return self


class ClaimMatch(BaseModel):
    result_key: str
    claim_type: str
    matched_term: str
    context: str
    severity: Literal["low", "medium", "high"]
    status: Literal["CLAIM_ENCONTRADO", "VALIDAR_TECNICAMENTE"]


class PipelineResult(BaseModel):
    job_id: str
    status: JobStatus
    report_path: str
    output_dir: str
    raw_count: int
    deduplicated_count: int
    score: dict[str, Any]
    providers: dict[str, Any]
