from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional

import requests

DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}


@dataclass
class HttpClient:
    timeout_sec: int = 30
    headers: Dict[str, str] = None
    session: Optional[requests.Session] = None

    def __post_init__(self) -> None:
        if self.headers is None:
            self.headers = dict(DEFAULT_HEADERS)
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update(self.headers)

    def get_text(self, url: str) -> str:
        # Небольшая задержка, чтобы не долбить сайт
        time.sleep(0.5)
        resp = self.session.get(url, timeout=self.timeout_sec)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or resp.encoding or "utf-8"
        return resp.text
