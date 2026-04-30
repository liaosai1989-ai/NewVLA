from __future__ import annotations

import shutil
from pathlib import Path

from bootstrap.copy_trees import copy_materialize_subtree
from bootstrap.workspace_path import validate_workspace_root_path


def _patch_runtime_webhook_pyproject(webhook_pyproject: Path) -> None:
    text = webhook_pyproject.read_text(encoding="utf-8")
    patched = text.replace("file:../vla_env_contract", "file:../../vla_env_contract")
    webhook_pyproject.write_text(patched, encoding="utf-8")


def materialize_workspace(
    *,
    clone_root: Path,
    workspace_root: Path,
    seed_env: Path | None = None,
    sync_env_from_clone: bool = False,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    validate_workspace_root_path(workspace_root, clone_root=clone_root)
    workspace_root.mkdir(parents=True, exist_ok=True)
    env_dst = workspace_root / ".env"
    clone_env = clone_root / ".env"
    if sync_env_from_clone:
        if not clone_env.is_file():
            raise FileNotFoundError(f"sync_env_from_clone but missing {clone_env}")
        if not dry_run:
            shutil.copy2(clone_env, env_dst)
    elif not env_dst.is_file():
        if clone_env.is_file():
            if not dry_run:
                shutil.copy2(clone_env, env_dst)
        elif seed_env is not None:
            if not seed_env.is_file():
                raise FileNotFoundError(f"seed_env is not a file: {seed_env}")
            if not dry_run:
                shutil.copy2(seed_env, env_dst)
        else:
            tmpl = clone_root / ".env.example"
            if not tmpl.is_file():
                raise SystemExit(
                    "工作区尚无 .env，且克隆根缺少 .env、.env.example 且无 --seed-env；"
                    "无法创建工作区根运行合同 .env（见 bootstrap/README.md）"
                )
            if not dry_run:
                shutil.copy2(tmpl, env_dst)

    agents_src = clone_root / "prompts" / "AGENTS.txt"
    if not agents_src.is_file():
        raise FileNotFoundError(f"missing {agents_src}")
    rules_src = clone_root / "prompts" / "rules"
    if not rules_src.is_dir():
        raise FileNotFoundError(f"missing directory {rules_src}")
    rules_dst = workspace_root / "rules"
    if rules_dst.exists() and any(rules_dst.iterdir()) and not force and not dry_run:
        raise SystemExit(
            "工作区 rules/ 已存在且非空；请加 --force 或先备份（见 bootstrap/README.md）"
        )
    if dry_run:
        return
    shutil.copy2(agents_src, workspace_root / "AGENTS.md")
    if rules_dst.exists():
        shutil.rmtree(rules_dst)
    shutil.copytree(rules_src, rules_dst)
    tools = workspace_root / "tools"
    tools.mkdir(exist_ok=True)

    vla_src = clone_root / "vla_env_contract"
    wh_src = clone_root / "webhook"
    if not vla_src.is_dir():
        raise FileNotFoundError(f"missing {vla_src}")
    if not wh_src.is_dir():
        raise FileNotFoundError(f"missing {wh_src}")

    copy_materialize_subtree(vla_src, workspace_root / "vla_env_contract", dry_run=dry_run)
    copy_materialize_subtree(wh_src, workspace_root / "runtime" / "webhook", dry_run=dry_run)
    wh_toml = workspace_root / "runtime" / "webhook" / "pyproject.toml"
    if wh_toml.is_file():
        _patch_runtime_webhook_pyproject(wh_toml)

    copy_materialize_subtree(
        clone_root / "dify_upload", tools / "dify_upload", dry_run=dry_run
    )
    copy_materialize_subtree(
        clone_root / "feishu_fetch", tools / "feishu_fetch", dry_run=dry_run
    )
