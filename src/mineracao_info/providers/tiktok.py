from __future__ import annotations
from typing import Any
from .base import Provider

class TikTokProvider(Provider):
    name = "tiktok"

    def build_input(self, seed: str, max_results: int, country: str) -> dict[str, Any]:
        payload = dict(self.defaults)
        payload.update({
            "searchQueries": [seed],
            "resultsPerPage": max_results,
        })
        # Alguns proxies do Actor podem nao aceitar BR; o usuario pode editar config/providers.yaml.
        return payload
