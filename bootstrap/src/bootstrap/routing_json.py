from __future__ import annotations

import json
from pathlib import Path


def load_pipeline_workspace_path_from_json(routes_file: Path) -> str:
    data = json.loads(routes_file.read_text(encoding="utf-8"))
    try:
        return str(data["pipeline_workspace"]["path"])
    except (KeyError, TypeError) as e:
        raise ValueError(f"invalid routing JSON: missing pipeline_workspace.path: {e}") from e
