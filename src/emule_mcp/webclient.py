from __future__ import annotations

import httpx

from .config import Config
from .errors import AuthenticationError, EMuleOfflineError
from .parsers import extract_session


class EMuleWebClient:
    """Minimal HTTP client for the classic eMule WebServer (port 4711)."""

    def __init__(self, config: Config, http_client: httpx.Client | None = None) -> None:
        self._config = config
        self._client = http_client or httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout_ms / 1000,
        )
        self._session_id: str | None = None

    def close(self) -> None:
        self._client.close()

    def fetch_page(self, page: str, **params: str) -> str:
        if self._session_id is None:
            self._login()

        html = self._request({"ses": self._session_id, "w": page, **params})
        if extract_session(html) is None:
            self._login()
            html = self._request({"ses": self._session_id, "w": page, **params})
        return html

    def _login(self) -> None:
        params = {"w": "password", "p": self._config.password}
        if self._config.user is not None:
            params["u"] = self._config.user

        html = self._request(params)
        session = extract_session(html)
        if session is None:
            raise AuthenticationError("eMule WebServer rejected the WebServer password")
        self._session_id = session

    def _request(self, params: dict[str, str]) -> str:
        try:
            response = self._client.get("/", params=params)
        except httpx.HTTPError as exc:
            raise EMuleOfflineError(
                f"cannot reach the eMule WebServer at {self._config.base_url}"
            ) from exc
        if response.status_code != httpx.codes.OK:
            raise EMuleOfflineError(
                f"eMule WebServer returned HTTP {response.status_code}"
            )
        return response.text
