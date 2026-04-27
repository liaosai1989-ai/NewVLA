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


def test_feishu_fetch_env_file_from_cwd_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    real = tmp_path / "real.env"
    real.write_text("FEISHU_APP_ID=cli_from_real\n", encoding="utf-8")
    primary = tmp_path / ".env"
    primary.write_text(
        f"FEISHU_FETCH_ENV_FILE={real.resolve().as_posix()}\n",
        encoding="utf-8",
    )
    s = load_feishu_fetch_settings()
    assert s.feishu_app_id == "cli_from_real"
    assert s.env_file.resolve() == real.resolve()
    assert s.workspace_root == real.parent


def test_os_environ_feishu_fetch_env_file_overrides_dotenv_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    real = tmp_path / "real.env"
    real.write_text("FEISHU_APP_ID=cli_real\n", encoding="utf-8")
    other = tmp_path / "other.env"
    other.write_text("FEISHU_APP_ID=cli_other\n", encoding="utf-8")
    primary = tmp_path / ".env"
    primary.write_text(
        f"FEISHU_FETCH_ENV_FILE={real.resolve().as_posix()}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FEISHU_FETCH_ENV_FILE", str(other.resolve()))
    s = load_feishu_fetch_settings()
    assert s.feishu_app_id == "cli_other"
    assert s.env_file.resolve() == other.resolve()


def test_timeout_must_be_positive(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "FEISHU_REQUEST_TIMEOUT_SECONDS=0\nFEISHU_APP_ID=x\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="FEISHU_REQUEST_TIMEOUT"):
        load_feishu_fetch_settings(env_file=env_file)
