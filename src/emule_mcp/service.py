from __future__ import annotations

import math
import time

from .parsers import (
    Download,
    SearchOutcome,
    Server,
    Status,
    extract_ed2k_hash,
    parse_downloads,
    parse_search,
    parse_servers,
    parse_status,
)
from .webclient import EMuleWebClient

SEARCH_WAIT_SECONDS = 10.0
SEARCH_POLL_SECONDS = 2.0


class EMuleService:
    """Application use cases over an eMule WebServer client."""

    def __init__(self, client: EMuleWebClient) -> None:
        self._client = client

    def get_status(self) -> Status:
        return parse_status(self._client.fetch_page("transfer"))

    def list_servers(self) -> tuple[Server, ...]:
        return parse_servers(self._client.fetch_page("server"))

    def connect(self, ip: str | None = None, port: int | None = None) -> Status:
        params = {"c": "connect"}
        if ip is not None:
            params["ip"] = ip
        if port is not None:
            params["port"] = str(port)
        self._client.fetch_page("server", **params)
        return self.get_status()

    def disconnect(self) -> Status:
        self._client.fetch_page("server", c="disconnect")
        return self.get_status()

    def list_downloads(self) -> tuple[Download, ...]:
        return parse_downloads(self._client.fetch_page("transfer"))

    def add_download(self, ed2k: str) -> Download | None:
        file_hash = extract_ed2k_hash(ed2k)
        param = ed2k.strip().replace(" ", "%20")
        downloads = parse_downloads(self._client.fetch_page("transfer", ed2k=param))
        return next(
            (item for item in downloads if item.file_hash.lower() == file_hash.lower()),
            None,
        )

    def search(
        self,
        query: str,
        method: str = "server",
        file_type: str | None = None,
        min_size_mb: int | None = None,
        max_size_mb: int | None = None,
        wait_seconds: float = SEARCH_WAIT_SECONDS,
        poll_seconds: float = SEARCH_POLL_SECONDS,
    ) -> SearchOutcome:
        params = {"tosearch": query, "method": method}
        if file_type:
            params["type"] = file_type
        if min_size_mb is not None:
            params["min"] = str(min_size_mb)
        if max_size_mb is not None:
            params["max"] = str(max_size_mb)

        outcome = parse_search(self._client.fetch_page("search", **params))
        collected = {result.file_hash: result for result in outcome.results}

        rounds = math.ceil(wait_seconds / poll_seconds) if poll_seconds > 0 else 0
        for _ in range(rounds):
            time.sleep(poll_seconds)
            page = parse_search(self._client.fetch_page("search"))
            for result in page.results:
                collected.setdefault(result.file_hash, result)

        return SearchOutcome(message=outcome.message, results=tuple(collected.values()))
