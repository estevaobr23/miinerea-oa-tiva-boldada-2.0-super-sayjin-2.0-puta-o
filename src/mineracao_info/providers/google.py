from __future__ import annotations
from typing import Any
from .base import Provider

class GoogleProvider(Provider):
    name = "google"

    def build_input(self, seed: str, max_results: int, country: str) -> dict[str, Any]:
        payload = dict(self.defaults)
        pages = max(1, min(10, (max_results + 9) // 10))
        payload.update({
            "queries": seed,
            "maxPagesPerQuery": pages,
            "countryCode": country.lower(),
            "languageCode": "pt",
        })
        return payload
