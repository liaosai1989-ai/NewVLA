from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def install_workspace_editables(workspace: Path) -> None:
    """BUG-007: pip install -e . per package with cwd=package (strict order)."""
    ws = workspace.resolve()
    dirs: tuple[Path, ...] = (
        ws / "vla_env_contract",
        ws / "runtime" / "webhook",
        ws / "tools" / "dify_upload",
        ws / "tools" / "feishu_fetch",
    )
    for d in dirs:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            check=True,
            cwd=str(d),
        )
