from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from dotenv import dotenv_values

from .config import DifyTargetConfig
from .upload import DifyConfigError


def _merged_dotenv_and_os(env_path: Path) -> dict[str, str]:
    """File values first; ``os.environ`` overrides (match webhook ``settings``)."""
    merged: dict[str, str] = {}
    if env_path.is_file():
        for k, v in (dotenv_values(env_path) or {}).items():
            if v is not None:
                merged[k] = v
    merged.update(dict(os.environ))
    return merged


def _parse_http_verify(raw: str) -> bool:
    s = raw.strip().lower()
    if s in ("true", "1", "yes", "on"):
        return True
    if s in ("false", "0", "no", "off"):
        return False
    raise DifyConfigError(
        f"dify config error: DIFY_TARGET_*_HTTP_VERIFY must be a boolean string; got {raw!r}"
    )


def _parse_timeout_seconds(raw: str) -> float:
    text = raw.strip()
    if not text:
        raise DifyConfigError(
            "dify config error: DIFY_TARGET_*_TIMEOUT_SECONDS is empty; set a positive number"
        )
    try:
        value = float(text)
    except ValueError as exc:
        raise DifyConfigError(
            f"dify config error: DIFY_TARGET_*_TIMEOUT_SECONDS is not a number; got {raw!r}"
        ) from exc
    return value


def resolve_dify_target(
    task_context: Mapping[str, Any], *, env_path: Path
) -> DifyTargetConfig:
    """Resolve ``DifyTargetConfig`` from ``task_context`` and ``DIFY_TARGET_<KEY>_`` keys in env.

    Keys per group (``onboard`` / root env contract): ``API_BASE``, ``API_KEY``,
    ``HTTP_VERIFY``, ``TIMEOUT_SECONDS``. ``dataset_id`` comes from ``task_context``.
    """
    try:
        raw_key = task_context["dify_target_key"]
    except KeyError as exc:
        raise DifyConfigError(
            "dify config error: task_context missing dify_target_key"
        ) from exc
    key = str(raw_key).strip().upper()
    if not key:
        raise DifyConfigError(
            "dify config error: dify_target_key is empty after strip"
        )

    try:
        dataset_raw = task_context["dataset_id"]
    except KeyError as exc:
        raise DifyConfigError(
            "dify config error: task_context missing dataset_id"
        ) from exc
    dataset_id = str(dataset_raw).strip()

    merged = _merged_dotenv_and_os(env_path)
    prefix = f"DIFY_TARGET_{key}_"
    api_base_key = f"{prefix}API_BASE"
    api_key_key = f"{prefix}API_KEY"
    verify_key = f"{prefix}HTTP_VERIFY"
    timeout_key = f"{prefix}TIMEOUT_SECONDS"

    def _get(name: str) -> str:
        raw_v = merged.get(name)
        return "" if raw_v is None else str(raw_v)

    api_base = _get(api_base_key).strip()
    api_key = _get(api_key_key).strip()
    http_raw = _get(verify_key)
    timeout_raw = _get(timeout_key)

    missing = [
        n
        for n, v in (
            (api_base_key, api_base),
            (api_key_key, api_key),
            (verify_key, http_raw.strip()),
            (timeout_key, timeout_raw.strip()),
        )
        if not v
    ]
    if missing:
        raise DifyConfigError(
            "dify config error: missing or empty env for Dify group "
            f"{key}: {', '.join(missing)}"
        )

    http_verify = _parse_http_verify(http_raw)
    timeout_seconds = _parse_timeout_seconds(timeout_raw)

    return DifyTargetConfig(
        api_base=api_base,
        api_key=api_key,
        dataset_id=dataset_id,
        http_verify=http_verify,
        timeout_seconds=timeout_seconds,
    )
