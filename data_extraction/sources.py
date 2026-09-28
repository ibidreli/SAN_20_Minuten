"""Austauschbare Quellen; nur HttpSource berührt das Netzwerk."""

import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

import requests

HTTP_TIMEOUT_SECONDS = 20
HTTP_MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1
RETRY_STATUS_CODES = {429, 503}
USER_AGENT = "SAN-F01/1.0 (FHNW research; article metadata extraction)"


class Source(Protocol):
    def fetch(self, url: str) -> tuple[int | None, str | None]: ...


class HttpSource:
    def fetch(self, url: str) -> tuple[int | None, str | None]:
        status = None
        for attempt in range(HTTP_MAX_ATTEMPTS):
            try:
                with requests.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=HTTP_TIMEOUT_SECONDS,
                    allow_redirects=False,
                ) as response:
                    status = response.status_code
                    if status not in RETRY_STATUS_CODES:
                        return status, response.text if status == 200 else None
            except requests.RequestException:
                status = None
            if attempt + 1 < HTTP_MAX_ATTEMPTS:
                time.sleep(BACKOFF_SECONDS * 2**attempt)
        return status, None


class FixtureSource:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.metadata = json.loads(
            (self.directory / "fixtures.json").read_text(encoding="utf-8")
        )

    def records(self, count: int) -> Iterator[tuple[str, str | None]]:
        names = list(self.metadata)
        for index in range(count):
            name = names[index % len(names)]
            year = self.metadata[name].get("jahr")
            yield f"fixture://{name}/{index}", f"{year}-01-01" if year else None

    def fetch(self, url: str) -> tuple[int, str | None]:
        parts = urlsplit(url)
        name = parts.netloc
        if parts.scheme != "fixture" or name not in self.metadata:
            raise ValueError("Unbekannte Fixture-URL")
        status = self.metadata[name].get("http", 200)
        if status != 200:
            return status, None
        return status, (self.directory / name).read_text(encoding="utf-8")
