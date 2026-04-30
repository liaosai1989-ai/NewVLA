from __future__ import annotations

import fnmatch
import shutil
from pathlib import Path

_EXCLUDED_DIR_NAMES = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
})


def materialize_copy_ignore(dirname: str, names: list[str]) -> list[str]:
    """Ignore callback for shutil.copytree (plan appendix A.1)."""
    ignored: list[str] = []
    for name in names:
        if name in _EXCLUDED_DIR_NAMES:
            ignored.append(name)
        elif fnmatch.fnmatch(name, "*.pyc"):
            ignored.append(name)
    return ignored


def copy_materialize_subtree(src: Path, dst: Path, *, dry_run: bool = False) -> None:
    if dry_run:
        return
    if not src.is_dir():
        raise FileNotFoundError(f"missing source directory: {src}")
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=materialize_copy_ignore)
