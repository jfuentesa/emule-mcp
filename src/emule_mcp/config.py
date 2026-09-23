from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from .errors import ConfigError

DEFAULT_BASE_URL = "http://127.0.0.1:4711"
DEFAULT_TIMEOUT_MS = 10_000


@dataclass(frozen=True)
class Config:
    base_url: str
    password: str
    user: str | None = None
    timeout_ms: int = DEFAULT_TIMEOUT_MS

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Config":
        source = os.environ if env is None else env

        password = source.get("EMULE_WEB_PASSWORD", "")
        if not password:
            raise ConfigError("EMULE_WEB_PASSWORD is not set")

        raw_timeout = source.get("EMULE_WEB_TIMEOUT_MS", str(DEFAULT_TIMEOUT_MS))
        try:
            timeout_ms = int(raw_timeout)
        except ValueError as exc:
            raise ConfigError("EMULE_WEB_TIMEOUT_MS must be an integer") from exc
        if timeout_ms <= 0:
            raise ConfigError("EMULE_WEB_TIMEOUT_MS must be positive")

        base_url = source.get("EMULE_WEB_URL", DEFAULT_BASE_URL).rstrip("/")
        user = source.get("EMULE_WEB_USER") or None

        return cls(base_url=base_url, password=password, user=user, timeout_ms=timeout_ms)
