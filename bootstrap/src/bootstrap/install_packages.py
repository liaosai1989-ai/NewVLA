from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_EDITABLE_PACKAGES = ("webhook", "onboard", "dify_upload", "feishu_fetch")


def _pip_run(args: list[str]) -> None:
    subprocess.run([sys.executable, "-m", "pip", *args], check=True)


def install_all(clone_root: Path) -> None:
    for name in _EDITABLE_PACKAGES:
        pkg = clone_root / name
        if not (pkg / "pyproject.toml").is_file():
            raise FileNotFoundError(f"missing package: {pkg}")
        _pip_run(["install", "-e", str(pkg)])
    _pip_run(["install", "markitdown"])
