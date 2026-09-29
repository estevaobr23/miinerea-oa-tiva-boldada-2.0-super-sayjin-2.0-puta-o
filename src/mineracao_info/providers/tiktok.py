from __future__ import annotations
from typing import Any
from .base import Provider

class TikTokProvider(Provider):
    name = "tiktok"

    def build_input(self, query: str, max_results: int, country: str, *, scrape_details: bool = False) -> dict[str, Any]:
        payload = dict(self.defaults)
        payload.update({
            "searchQueries": [query],
            "resultsPerPage": max_results,
            "downloadSubtitlesOptions": "NEVER_DOWNLOAD_SUBTITLES",
        })
        payload.pop("shouldDownloadSubtitles", None)
        return payload
