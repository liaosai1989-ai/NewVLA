from __future__ import annotations

from typing import Any

import httpx

from .config import DifyUploadConfig


class SimpleHttpPort:
    def __init__(
        self,
        *,
        verify: bool = True,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._client = client or httpx.Client(
            verify=verify,
            timeout=timeout,
            follow_redirects=True,
        )

    @classmethod
    def from_config(cls, config: DifyUploadConfig) -> "SimpleHttpPort":
        return cls(
            verify=config.http_verify,
            timeout=config.timeout_seconds,
        )

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        return self._client.request(method, url, **kwargs)

    def __enter__(self) -> "SimpleHttpPort":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()
