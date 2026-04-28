from pathlib import Path

import pytest

from dify_upload.config import DifyTargetConfig
from dify_upload.resolve_target import resolve_dify_target
from dify_upload.upload import DifyConfigError


def test_resolve_dify_target_reads_dotenv_and_task_context(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "DIFY_TARGET_MYKEY_API_BASE=https://dify.example.com",
                "DIFY_TARGET_MYKEY_API_KEY=secret-key",
                "DIFY_TARGET_MYKEY_HTTP_VERIFY=false",
                "DIFY_TARGET_MYKEY_TIMEOUT_SECONDS=42.5",
                "",
            ]
        ),
        encoding="utf-8",
    )
    ctx = {"dify_target_key": " mykey ", "dataset_id": " ds-1 "}
    cfg = resolve_dify_target(ctx, env_path=env_file)
    assert isinstance(cfg, DifyTargetConfig)
    assert cfg.api_base == "https://dify.example.com"
    assert cfg.api_key == "secret-key"
    assert cfg.dataset_id == "ds-1"
    assert cfg.http_verify is False
    assert cfg.timeout_seconds == 42.5


def test_resolve_raises_when_group_incomplete(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DIFY_TARGET_X_API_BASE=https://a\n",
        encoding="utf-8",
    )
    ctx = {"dify_target_key": "X", "dataset_id": "d1"}
    with pytest.raises(DifyConfigError, match="missing or empty"):
        resolve_dify_target(ctx, env_path=env_file)


def test_resolve_raises_when_dify_target_key_missing() -> None:
    with pytest.raises(DifyConfigError, match="missing dify_target_key"):
        resolve_dify_target({}, env_path=Path("/nonexistent/.env"))
