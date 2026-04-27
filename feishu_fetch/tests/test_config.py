from __future__ import annotations

from pathlib import Path

import pytest

from feishu_fetch.config import load_feishu_fetch_settings


def test_load_minimal_env(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "FEISHU_REQUEST_TIMEOUT_SECONDS=90",
                "FEISHU_APP_ID=cli_abc",
            ]
        ),
        encoding="utf-8",
    )
    s = load_feishu_fetch_settings(env_file=env_file)
    assert s.request_timeout_seconds == 90.0
    assert s.feishu_app_id == "cli_abc"
    assert s.workspace_root == env_file.resolve().parent


def test_rejects_deprecated_lark_cli_command_in_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LARK_CLI_COMMAND=lark-cli\n"
        "FEISHU_REQUEST_TIMEOUT_SECONDS=60\n"
        "FEISHU_APP_ID=cli_x\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="LARK_CLI_COMMAND"):
        load_feishu_fetch_settings(env_file=env_file)


def test_timeout_must_be_positive(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "FEISHU_REQUEST_TIMEOUT_SECONDS=0\nFEISHU_APP_ID=x\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="FEISHU_REQUEST_TIMEOUT"):
        load_feishu_fetch_settings(env_file=env_file)
