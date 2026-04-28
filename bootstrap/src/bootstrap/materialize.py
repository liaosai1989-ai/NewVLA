from __future__ import annotations

import shutil
import sys
from pathlib import Path

from bootstrap.junction import ensure_junction
from bootstrap.workspace_path import validate_workspace_root_path


def materialize_workspace(
    *,
    clone_root: Path,
    workspace_root: Path,
    link_tools: bool,
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
    if link_tools and sys.platform == "win32":
        ensure_junction(tools / "dify_upload", clone_root / "dify_upload")
        ensure_junction(tools / "feishu_fetch", clone_root / "feishu_fetch")
    elif link_tools:
        raise RuntimeError("link_tools requires Windows")
    else:
        (tools / "dify_upload").mkdir(parents=True, exist_ok=True)
        (tools / "feishu_fetch").mkdir(parents=True, exist_ok=True)
