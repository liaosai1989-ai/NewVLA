from pathlib import Path

from bootstrap.materialize import materialize_workspace


def _is_descendant(child: Path, ancestor: Path) -> bool:
    try:
        child.resolve().relative_to(ancestor.resolve())
        return True
    except ValueError:
        return False


def _minimal_clone(clone: Path, env_example_body: str) -> None:
    (clone / ".env.example").write_text(env_example_body, encoding="utf-8")
    for sub, body in (
        (
            "vla_env_contract",
            "[project]\nname=dummy-vla\nversion=0\n",
        ),
        ("webhook", "[project]\nname=dummy-wh\nversion=0\n"),
        ("dify_upload", "[project]\nname=dummy-du\nversion=0\n"),
        ("feishu_fetch", "[project]\nname=dummy-ff\nversion=0\n"),
    ):
        d = clone / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / "pyproject.toml").write_text(body, encoding="utf-8")
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
    materialize_workspace(clone_root=clone, workspace_root=ws, seed_env=None)
    assert (ws / ".env").read_text(encoding="utf-8") == "KEEP=secret\n"


def test_materialize_copies_webhook_runtime_and_vla_env_contract(tmp_path):
    clone = tmp_path / "clone"
    ws = tmp_path / "ws"
    clone.mkdir()
    (clone / ".env").write_text("K=v\n", encoding="utf-8")
    (clone / ".env.example").write_text("K=v\n", encoding="utf-8")
    (clone / "prompts").mkdir(parents=True)
    (clone / "prompts" / "AGENTS.txt").write_text("a", encoding="utf-8")
    (clone / "prompts" / "rules").mkdir(parents=True)
    (clone / "vla_env_contract").mkdir(parents=True)
    (clone / "vla_env_contract" / "pyproject.toml").write_text(
        "[project]\nname=dummy-vla-env\n", encoding="utf-8"
    )
    (clone / "webhook").mkdir(parents=True)
    (clone / "webhook" / "pyproject.toml").write_text(
        '[project]\nname=dummy-wh\ndependencies = ["vla-env-contract @ file:../vla_env_contract"]\n',
        encoding="utf-8",
    )
    (clone / "dify_upload").mkdir(parents=True)
    (clone / "dify_upload" / "pyproject.toml").write_text("[project]\nname=x\n", encoding="utf-8")
    (clone / "feishu_fetch").mkdir(parents=True)
    (clone / "feishu_fetch" / "pyproject.toml").write_text("[project]\nname=y\n", encoding="utf-8")
    materialize_workspace(
        clone_root=clone,
        workspace_root=ws,
        seed_env=None,
    )
    assert (ws / "runtime" / "webhook" / "pyproject.toml").is_file()
    assert (ws / "vla_env_contract" / "pyproject.toml").is_file()
    assert (ws / "tools" / "dify_upload" / "pyproject.toml").is_file()
    assert not (ws / "onboard").exists()
    wh_toml = (ws / "runtime" / "webhook" / "pyproject.toml").read_text(encoding="utf-8")
    assert "file:../../vla_env_contract" in wh_toml
    assert "file:../vla_env_contract" not in wh_toml


def test_materialize_tools_are_real_directories(tmp_path):
    clone = tmp_path / "clone"
    ws = tmp_path / "ws"
    clone.mkdir()
    _minimal_clone(clone, "K=v\n")
    materialize_workspace(clone_root=clone, workspace_root=ws, seed_env=None)
    du = (ws / "tools" / "dify_upload").resolve()
    assert _is_descendant(du, ws.resolve())


def test_materialize_copies_non_py_resource(tmp_path):
    clone = tmp_path / "clone"
    ws = tmp_path / "ws"
    clone.mkdir()
    _minimal_clone(clone, "K=v\n")
    data = clone / "dify_upload" / "data"
    data.mkdir(parents=True)
    (data / "foo.json").write_text("{}", encoding="utf-8")
    materialize_workspace(clone_root=clone, workspace_root=ws, seed_env=None)
    assert (ws / "tools" / "dify_upload" / "data" / "foo.json").read_text(encoding="utf-8") == "{}"
