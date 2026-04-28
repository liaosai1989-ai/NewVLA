from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _resolve_clone_root(path: Path | None) -> Path:
    from bootstrap.paths import assert_clone_root_looks_sane, default_clone_root

    root = path if path is not None else default_clone_root()
    try:
        return assert_clone_root_looks_sane(root)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(2) from e


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bootstrap")
    sub = p.add_subparsers(dest="cmd", required=True)

    setup_p = sub.add_parser(
        "interactive-setup",
        help="人机验收主入口：编排 install → materialize → 编辑提示 → doctor（spec §7）",
    )
    setup_p.add_argument("--dry-run", action="store_true")
    setup_p.add_argument(
        "--yes",
        action="store_true",
        help="skip Enter prompt before doctor",
    )

    doctor_p = sub.add_parser("doctor", help="环境自检（CI/排障）")
    doctor_p.add_argument("--workspace", type=Path, required=True)
    doctor_p.add_argument("--clone-root", type=Path, default=None)

    install_p = sub.add_parser("install-packages", help="pip install -e 子包 + markitdown")
    install_p.add_argument("--clone-root", type=Path, default=None)

    mat_p = sub.add_parser("materialize-workspace", help="物化执行工作区（CI/排障）")
    mat_p.add_argument("--workspace", type=Path, required=True)
    mat_p.add_argument("--clone-root", type=Path, default=None)
    mat_p.add_argument("--sync-env-from-clone", action="store_true")
    mat_p.add_argument("--seed-env", type=Path, default=None)
    mat_p.add_argument("--dry-run", action="store_true")
    mat_p.add_argument("--force", action="store_true")

    ns = p.parse_args(argv)

    if ns.cmd == "interactive-setup":
        from bootstrap.interactive_setup import run_interactive_setup

        return run_interactive_setup(
            dry_run=ns.dry_run,
            yes=ns.yes,
        )

    if ns.cmd == "doctor":
        clone = _resolve_clone_root(ns.clone_root)
        from bootstrap.doctor import run_doctor

        return run_doctor(clone_root=clone, workspace=ns.workspace.resolve())

    if ns.cmd == "install-packages":
        clone = _resolve_clone_root(ns.clone_root)
        from bootstrap.install_packages import install_all

        install_all(clone)
        return 0

    if ns.cmd == "materialize-workspace":
        clone = _resolve_clone_root(ns.clone_root)
        from bootstrap.materialize import materialize_workspace

        try:
            materialize_workspace(
                clone_root=clone,
                workspace_root=ns.workspace.resolve(),
                seed_env=ns.seed_env,
                sync_env_from_clone=ns.sync_env_from_clone,
                dry_run=ns.dry_run,
                force=ns.force,
            )
        except SystemExit as e:
            msg = e.args[0] if e.args else ""
            if isinstance(msg, str) and msg:
                print(msg, file=sys.stderr)
            code = e.code
            if isinstance(code, int):
                return code
            return 1
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
