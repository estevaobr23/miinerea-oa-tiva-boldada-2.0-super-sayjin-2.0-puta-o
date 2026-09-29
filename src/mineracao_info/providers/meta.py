from __future__ import annotations
from typing import Any
from .base import Provider

class MetaProvider(Provider):
    name = "meta"

    def build_input(self, query: str, max_results: int, country: str, *, scrape_details: bool = False) -> dict[str, Any]:
        payload = dict(self.defaults)
        payload.update({
            "searchTerms": [query],
            "pageUrls": [],
            "startUrls": [],
            "country": country.upper(),
            "maxResults": max_results,
            "scrapeAdDetails": bool(scrape_details),
            "onlyTotalCount": False,
        })
        return payload

    def build_preflight_input(self, query: str, country: str) -> dict[str, Any]:
        payload = dict(self.defaults)
        payload.update({
            "searchTerms": [query],
            "pageUrls": [],
            "startUrls": [],
            "country": country.upper(),
            "onlyTotalCount": True,
            "scrapeAdDetails": False,
            "includeAboutPage": False,
        })
        payload.pop("maxResults", None)
        return payload
