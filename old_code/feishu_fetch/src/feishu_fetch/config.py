from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlparse

_ALLOWED_HOSTS = {"open.feishu.cn"}


def _env_float(raw: str | None, default: float) -> float:
    if raw is None or not raw.strip():
        return default
    return float(raw)


def _validate_api_base(value: str) -> str:
    base = value.rstrip("/")
    parsed = urlparse(base)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in _ALLOWED_HOSTS
        or parsed.port is not None
        or parsed.path not in ("", "/")
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("feishu_api_base must be https://open.feishu.cn")
    return base


@dataclass(frozen=True)
class FeishuFetchConfig:
    feishu_app_id: str
    feishu_app_secret: str
    feishu_api_base: str = "https://open.feishu.cn"
    request_timeout_seconds: float = 60.0
    verify_ssl: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "feishu_api_base", _validate_api_base(self.feishu_api_base)
        )
        if (
            not math.isfinite(self.request_timeout_seconds)
            or self.request_timeout_seconds <= 0
        ):
            raise ValueError("request_timeout_seconds must be finite and > 0")

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
    ) -> "FeishuFetchConfig":
        source = os.environ if env is None else env
        return cls(
            feishu_app_id=source["FEISHU_APP_ID"],
            feishu_app_secret=source["FEISHU_APP_SECRET"],
            request_timeout_seconds=_env_float(
                source.get("FEISHU_REQUEST_TIMEOUT_SECONDS"),
                60.0,
            ),
        )
