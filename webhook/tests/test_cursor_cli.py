import json

from webhook_cursor_executor.cursor_cli import ensure_max_mode_config


def test_ensure_max_mode_config_creates_minimal_file(tmp_path):
    config_path = tmp_path / "cli-config.json"
    ensure_max_mode_config(config_path=config_path)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["maxMode"] is True
    assert payload["model"]["maxMode"] is True
