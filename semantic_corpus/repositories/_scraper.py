"""Shared HTTP scraping helpers for repository adapters."""

import time
from typing import Dict, Optional

import requests


class RateLimitedSession:
    """Simple rate-limited requests session for polite scraping."""

    def __init__(self, delay_seconds: float = 1.0, user_agent: str = "") -> None:
        self.delay_seconds = delay_seconds
        self.last_request_time = 0.0
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent
                or (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36 semantic_corpus/0.1"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def _rate_limit(self) -> None:
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        self.last_request_time = time.time()

    def get(
        self,
        url: str,
        *,
        params: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> Optional[requests.Response]:
        """GET with rate limiting; return None on failure."""
        self._rate_limit()
        try:
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException:
            return None
