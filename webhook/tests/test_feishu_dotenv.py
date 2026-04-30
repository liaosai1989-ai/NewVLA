"""Tests for webhook/scripts/feishu_dotenv.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import feishu_dotenv as fd  # noqa: E402


def test_bootstrap_only_via_find(monkeypatch, tmp_path):
    boot = tmp_path / ".env"
    boot.write_text("FEISHU_APP_ID=x\n", encoding="utf-8")
    monkeypatch.setattr(fd, "find_bootstrap_env_path", lambda: boot.resolve())
    assert fd.load_dotenv_flat()["FEISHU_APP_ID"] == "x"


def test_clone_dotenv_vla_key_is_plain_kv(monkeypatch, tmp_path):
    """文件里的 VLA_WORKSPACE_ROOT 只是普通键，不参与切换加载路径。"""
    ws = tmp_path / "ws"
    ws.mkdir()
    boot = tmp_path / ".env"
    boot.write_text(
        f"VLA_WORKSPACE_ROOT={ws}\nFEISHU_APP_ID=from_clone\n",
        encoding="utf-8",
    )
    (ws / ".env").write_text("FEISHU_APP_ID=from_ws\n", encoding="utf-8")
    monkeypatch.setattr(fd, "find_bootstrap_env_path", lambda: boot.resolve())
    d = fd.load_dotenv_flat()
    assert d["FEISHU_APP_ID"] == "from_clone"
