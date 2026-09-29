from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class Provider(ABC):
    name: str

    def __init__(self, actor_id: str, defaults: dict[str, Any] | None = None):
        self.actor_id = actor_id
        self.defaults = defaults or {}

    @abstractmethod
    def build_input(self, query: str, max_results: int, country: str, *, scrape_details: bool = False) -> dict[str, Any]:
        raise NotImplementedError

    def build_preflight_input(self, query: str, country: str) -> dict[str, Any] | None:
        return None
