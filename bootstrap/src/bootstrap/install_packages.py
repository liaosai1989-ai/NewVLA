from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_EDITABLE_PACKAGES = (
    "vla_env_contract",
    "webhook",
    "onboard",
    "dify_upload",
    "feishu_fetch",
)


def _pip_run(args: list[str], *, cwd: str | None = None) -> None:
    # cwd + "-e ." avoids pip/file: URL resolution bugs on Windows when the editable
    # target is passed as an absolute path and the clone path contains spaces (BUG-007).
    subprocess.run(
        [sys.executable, "-m", "pip", *args],
        check=True,
        cwd=cwd,
    )


def install_all(clone_root: Path) -> None:
    for name in _EDITABLE_PACKAGES:
        pkg = clone_root / name
        if not (pkg / "pyproject.toml").is_file():
            raise FileNotFoundError(f"missing package: {pkg}")
        _pip_run(["install", "-e", "."], cwd=str(pkg.resolve()))
    _pip_run(["install", "markitdown"])
