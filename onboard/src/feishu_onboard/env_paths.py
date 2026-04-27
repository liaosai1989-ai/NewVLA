from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    override = (os.environ.get("FEISHU_ONBOARD_REPO_ROOT") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def root_dotenv_path() -> Path:
    return repo_root() / ".env"
