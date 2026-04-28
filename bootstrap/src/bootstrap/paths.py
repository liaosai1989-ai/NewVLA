from __future__ import annotations

from pathlib import Path


def default_clone_root() -> Path:
    return Path(__file__).resolve().parents[3]


def assert_clone_root_looks_sane(root: Path) -> Path:
    r = root.expanduser().resolve()
    wh = r / "webhook" / "pyproject.toml"
    bs = r / "bootstrap" / "pyproject.toml"
    if not wh.is_file() or not bs.is_file():
        raise ValueError(
            "clone root does not look like this repo root "
            f"(missing webhook/pyproject.toml or bootstrap/pyproject.toml): {r}. "
            "Use --clone-root <absolute path to cloned repo> or pip install -e ./bootstrap."
        )
    return r
