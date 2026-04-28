import sys
from pathlib import Path

import pytest

from bootstrap.materialize import materialize_workspace


def _minimal_clone(clone: Path, env_example_body: str) -> None:
    (clone / ".env.example").write_text(env_example_body, encoding="utf-8")
    (clone / "dify_upload").mkdir(parents=True)
    (clone / "feishu_fetch").mkdir(parents=True)
    prompts = clone / "prompts"
    rules = prompts / "rules" / "qa"
    rules.mkdir(parents=True)
    (rules / "x.mdc").write_text("rule", encoding="utf-8")
    (prompts / "AGENTS.txt").write_text("agents", encoding="utf-8")


def test_materialize_seeds_workspace_env_from_clone_dotenv_when_present(tmp_path):
    clone = tmp_path / "clone"
    ws = tmp_path / "ws"
    clone.mkdir()
    _minimal_clone(clone, "FROM_EXAMPLE=only\n")
    (clone / ".env").write_text("FROM_CLONE=1\n", encoding="utf-8")
    materialize_workspace(
        clone_root=clone,
        workspace_root=ws,
        link_tools=sys.platform == "win32",
        seed_env=None,
    )
    assert (ws / ".env").read_text(encoding="utf-8") == "FROM_CLONE=1\n"


def test_materialize_seeds_workspace_env_from_dotenv_example_when_no_clone_dotenv(tmp_path):
    clone = tmp_path / "clone"
    ws = tmp_path / "ws"
    clone.mkdir()
    _minimal_clone(clone, "K=v\n")
    materialize_workspace(
        clone_root=clone,
        workspace_root=ws,
        link_tools=sys.platform == "win32",
        seed_env=None,
    )
    assert (ws / ".env").read_text(encoding="utf-8") == "K=v\n"
    assert (ws / "AGENTS.md").read_text(encoding="utf-8") == "agents"
    assert (ws / "rules" / "qa" / "x.mdc").read_text(encoding="utf-8") == "rule"
    assert (ws / ".cursor_task").exists() is False


def test_materialize_does_not_overwrite_existing_workspace_env(tmp_path):
    clone = tmp_path / "clone"
    ws = tmp_path / "ws"
    clone.mkdir()
    _minimal_clone(clone, "FROM_TEMPLATE=1\n")
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".env").write_text("KEEP=secret\n", encoding="utf-8")
    materialize_workspace(clone_root=clone, workspace_root=ws, link_tools=False, seed_env=None)
    assert (ws / ".env").read_text(encoding="utf-8") == "KEEP=secret\n"


@pytest.mark.skipif(sys.platform != "win32", reason="tools junction only on win")
def test_materialize_tools_junctions(tmp_path):
    clone = tmp_path / "clone"
    (clone / "dify_upload" / "src").mkdir(parents=True)
    (clone / "feishu_fetch" / "src").mkdir(parents=True)
    (clone / ".env.example").write_text("x=1\n", encoding="utf-8")
    (clone / "prompts").mkdir(parents=True)
    (clone / "prompts" / "AGENTS.txt").write_text("a", encoding="utf-8")
    (clone / "prompts" / "rules").mkdir(parents=True)
    ws = tmp_path / "ws"
    materialize_workspace(clone_root=clone, workspace_root=ws, link_tools=True, seed_env=None)
    assert (ws / "tools" / "dify_upload" / "src").is_dir()
