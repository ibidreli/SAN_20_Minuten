"""Abrufschicht; HttpSource ist die einzige Stelle mit Netzwerkzugriff."""

import time
from typing import Protocol

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
