from __future__ import annotations
from typing import Any
from .base import Provider

class MetaProvider(Provider):
    name = "meta"

    def build_input(self, seed: str, max_results: int, country: str) -> dict[str, Any]:
        payload = dict(self.defaults)
        payload.update({
            "searchTerms": [seed],
            "pageUrls": [],
            "startUrls": [],
            "country": country.upper(),
            "maxResults": max_results,
        })
        return payload
