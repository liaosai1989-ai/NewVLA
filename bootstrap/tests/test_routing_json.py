import json
from pathlib import Path

from bootstrap.routing_json import load_pipeline_workspace_path_from_json


def test_load_pipeline_workspace_path_from_json(tmp_path):
    j = tmp_path / "r.json"
    j.write_text(
        json.dumps({"pipeline_workspace": {"path": r"D:\a\b", "cursor_timeout_seconds": 1}}),
        encoding="utf-8",
    )
    assert load_pipeline_workspace_path_from_json(j) == r"D:\a\b"
