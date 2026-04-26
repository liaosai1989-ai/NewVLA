from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DifyUploadConfig:
    api_base: str
    api_key: str
    dataset_id: str
    http_verify: bool = True
    timeout_seconds: float = 60.0

    @property
    def api_base_v1(self) -> str:
        base = self.api_base.strip().rstrip("/")
        if base.endswith("/v1"):
            return base
        return f"{base}/v1"
