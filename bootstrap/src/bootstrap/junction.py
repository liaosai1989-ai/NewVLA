from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def ensure_junction(link: Path, target: Path) -> None:
    if sys.platform != "win32":
        raise RuntimeError("junction strategy requires Windows (spec P0)")
    target_r = target.resolve()
    if not target_r.is_dir():
        raise FileNotFoundError(f"junction target must exist: {target_r}")
    if link.exists():
        if not link.is_dir():
            raise FileExistsError(f"path exists and is not a directory: {link}")
        if link.resolve() == target_r:
            return
        raise FileExistsError(
            f"path exists and resolves to {link.resolve()!s}, not junction target {target_r!s}: {link}"
        )
    link.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target_r)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "mklink /J failed:\n" + (proc.stderr or proc.stdout or "").strip()
        )
