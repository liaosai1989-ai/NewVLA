from __future__ import annotations

from dataclasses import dataclass


def _raise_config_error(message: str) -> None:
    from .upload import DifyConfigError

    raise DifyConfigError(message)


def _require_non_empty(value: str, *, field_name: str, hint: str) -> str:
    text = str(value).strip()
    if not text:
        _raise_config_error(f"dify config error: {field_name} is empty; {hint}")
    return text


@dataclass(frozen=True)
class DifyTargetConfig:
    api_base: str
    api_key: str
    dataset_id: str
    http_verify: bool = True
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        api_base = _require_non_empty(
            self.api_base,
            field_name="api_base",
            hint="resolve target config before calling upload",
        )
        api_key = _require_non_empty(
            self.api_key,
            field_name="api_key",
            hint="resolve target config before calling upload",
        )
        dataset_id = _require_non_empty(
            self.dataset_id,
            field_name="dataset_id",
            hint="caller must provide dataset_id before upload",
        )
        if self.timeout_seconds <= 0:
            _raise_config_error(
                "dify config error: timeout_seconds must be > 0; caller must provide a positive timeout"
            )
        object.__setattr__(self, "api_base", api_base)
        object.__setattr__(self, "api_key", api_key)
        object.__setattr__(self, "dataset_id", dataset_id)

    @property
    def api_base_v1(self) -> str:
        base = self.api_base.strip().rstrip("/")
        if base.endswith("/v1"):
            return base
        return f"{base}/v1"
