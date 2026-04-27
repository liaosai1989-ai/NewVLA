from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import subprocess

from feishu_onboard.lark_cli import (
    _resolve_lark_cli_exe,
    lark_config_init,
    lark_config_init_excerpt_for_failure,
    lark_config_show_verify_app_id,
)

_WHICH = r"C:\fake\lark-cli.cmd"


@patch("feishu_onboard.lark_cli.shutil.which", return_value=_WHICH)
@patch("feishu_onboard.lark_cli.subprocess.run")
def test_config_init_sends_secret_on_stdin_not_argv(
    mock_run: MagicMock, _mock_which: MagicMock, tmp_path: Path
) -> None:
    mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
    lark_config_init(tmp_path, "cli_abc", "secret123", lark_command="lark-cli")
    call_kw = mock_run.call_args.kwargs
    assert call_kw.get("input") == b"secret123" or (
        call_kw.get("input") == "secret123".encode("utf-8")
    )
    argv = mock_run.call_args[0][0]
    assert "secret123" not in " ".join(argv)
    assert "--app-id" in argv or "config" in argv
    assert argv[0] == _WHICH


@patch("feishu_onboard.lark_cli.shutil.which", return_value=_WHICH)
@patch("feishu_onboard.lark_cli.subprocess.run")
def test_config_show_parses_app_id(mock_run: MagicMock, _m: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=b'{"appId":"cli_abc"}\n',
        stderr=b"",
    )
    lark_config_show_verify_app_id(tmp_path, "cli_abc", lark_command="lark-cli")
    show_argv = mock_run.call_args[0][0]
    assert show_argv[1:3] == ["config", "show"]
    assert "--json" not in show_argv


@patch("feishu_onboard.lark_cli.shutil.which", return_value=_WHICH)
@patch("feishu_onboard.lark_cli.subprocess.run")
def test_config_show_mismatch_raises(mock_run: MagicMock, _m: MagicMock, tmp_path: Path) -> None:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=b'{"appId":"other"}\n',
        stderr=b"",
    )
    with pytest.raises(ValueError, match="appId|一致"):
        lark_config_show_verify_app_id(tmp_path, "cli_abc", lark_command="lark-cli")


@patch("feishu_onboard.lark_cli.shutil.which", return_value=r"C:\n\lark-cli.CMD")
def test_resolve_uses_shutil_which(_mock_which: MagicMock) -> None:
    assert _resolve_lark_cli_exe("lark-cli") == r"C:\n\lark-cli.CMD"


def test_resolve_missing_raises() -> None:
    with patch("feishu_onboard.lark_cli.shutil.which", return_value=None):
        with pytest.raises(FileNotFoundError, match="PATH"):
            _resolve_lark_cli_exe("lark-cli")


def test_init_failure_excerpt_includes_stderr() -> None:
    p = subprocess.CompletedProcess(["x"], 1, b"", b"auth failed\n")
    s = lark_config_init_excerpt_for_failure(p)
    assert "退出码=1" in s
    assert "stderr" in s
    assert "auth failed" in s
