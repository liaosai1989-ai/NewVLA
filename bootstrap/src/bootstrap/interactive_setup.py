from __future__ import annotations

from pathlib import Path
from typing import Callable

from bootstrap.doctor import run_doctor
from bootstrap.install_packages import install_all
from bootstrap.materialize import materialize_workspace
from bootstrap.paths import assert_clone_root_looks_sane
from bootstrap.workspace_path import validate_workspace_root_path


def run_interactive_setup(
    *,
    dry_run: bool,
    yes: bool,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[..., None] = print,
) -> int:
    print_fn("bootstrap interactive-setup — 人机验收主路径（控制台 UTF-8）")
    clone_root = Path.cwd().resolve()
    while True:
        try:
            clone_root = assert_clone_root_looks_sane(clone_root)
            break
        except ValueError as e:
            print_fn(str(e))
            line = input_fn("Enter clone root absolute path (empty=abort): ").strip()
            if not line:
                return 2
            clone_root = Path(line).expanduser().resolve()

    while True:
        line = input_fn("Workspace root absolute path (required): ").strip()
        if not line:
            print_fn("workspace path required")
            continue
        ws = Path(line).expanduser()
        try:
            ws = validate_workspace_root_path(ws, clone_root=clone_root)
            break
        except ValueError as e:
            print_fn(str(e))

    print_fn("Running install-packages…")
    install_all(clone_root)
    print_fn("Running materialize-workspace…")
    materialize_workspace(
        clone_root=clone_root,
        workspace_root=ws,
        seed_env=None,
        sync_env_from_clone=False,
        dry_run=dry_run,
        force=False,
    )
    print_fn(f"Edit workspace .env with your editor: {ws / '.env'}")
    print_fn(
        "Routing contract (§7): prefer FEISHU_FOLDER_ROUTE_KEYS + FEISHU_FOLDER_<KEY>_* "
        "in workspace .env; FOLDER_ROUTES_FILE JSON is legacy fallback only."
    )
    print_fn(
        "Next manually: feishu-onboard (merge keys into workspace .env); "
        "set VLA_WORKSPACE_ROOT to same path as workspace; start Redis/webhook."
    )
    if not yes:
        input_fn("Press Enter to run doctor… ")
    return run_doctor(clone_root=clone_root, workspace=ws)
