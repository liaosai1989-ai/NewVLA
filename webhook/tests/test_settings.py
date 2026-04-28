import json

import pytest

from webhook_cursor_executor import settings as settings_mod
from webhook_cursor_executor.settings import (
    ExecutorSettings,
    _raise_if_env_file_bans_cursor_cli_command,
    load_routing_config,
)


def test_settings_defaults_and_route_loading(tmp_path, monkeypatch):
    ws = tmp_path / "iso_ws"
    ws.mkdir()
    (ws / ".env").write_text(
        "DOC_RUNLOCK_TTL_SECONDS=10800\nCURSOR_RUN_TIMEOUT_SECONDS=7200\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("VLA_WORKSPACE_ROOT", str(ws))
    settings_mod.get_executor_settings.cache_clear()

    routes_file = tmp_path / "routes.json"
    routes_file.write_text(
        """
        {
          "pipeline_workspace": {
            "path": "C:\\\\workspaces\\\\pipeline",
            "cursor_timeout_seconds": 7200
          },
          "folder_routes": [
            {
              "folder_token": "fld_team_a",
              "qa_rule_file": "rules/team_a_qa.md",
              "dataset_id": "dataset_team_a"
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    settings = ExecutorSettings(folder_routes_file=str(routes_file))
    routing = load_routing_config(settings)

    assert settings.feishu_webhook_path == "/webhook/feishu"
    assert settings.cursor_cli_model == "composer-2-fast"
    assert settings.doc_runlock_ttl_seconds >= settings.cursor_run_timeout_seconds
    assert routing.folder_routes[0].dataset_id == "dataset_team_a"


def test_env_file_rejects_cursor_cli_command_key(tmp_path):
    p = tmp_path / ".env"
    p.write_text("CURSOR_CLI_COMMAND=cursor\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CURSOR_CLI_COMMAND"):
        _raise_if_env_file_bans_cursor_cli_command(path=p)


def test_env_file_uses_vla_workspace_root(tmp_path, monkeypatch):
    ws = tmp_path / "workspace"
    ws.mkdir()
    env_f = ws / ".env"
    env_f.write_text("REDIS_URL=redis://from-workspace-env:9/0\n", encoding="utf-8")
    monkeypatch.setenv("VLA_WORKSPACE_ROOT", str(ws))
    settings_mod.get_executor_settings.cache_clear()
    st = ExecutorSettings()
    assert st.redis_url == "redis://from-workspace-env:9/0"


def test_settings_reject_cursor_cli_command_in_environ(
    tmp_path, monkeypatch
) -> None:
    ws = tmp_path / "iso_ws2"
    ws.mkdir()
    (ws / ".env").write_text(
        "DOC_RUNLOCK_TTL_SECONDS=10800\nCURSOR_RUN_TIMEOUT_SECONDS=7200\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("VLA_WORKSPACE_ROOT", str(ws))
    settings_mod.get_executor_settings.cache_clear()

    routes = tmp_path / "routes.json"
    routes.write_text(
        """
        {
          "pipeline_workspace": {
            "path": "C:\\\\workspaces\\\\pipeline",
            "cursor_timeout_seconds": 7200
          },
          "folder_routes": []
        }
        """.strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("CURSOR_CLI_COMMAND", "cursor")
    with pytest.raises(ValueError, match="CURSOR_CLI_COMMAND"):
        ExecutorSettings(folder_routes_file=str(routes))


def test_load_routing_from_env_keys(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    ws.mkdir()
    env_file = ws / ".env"
    env_file.write_text(
        "\n".join(
            [
                f"VLA_WORKSPACE_ROOT={ws}",
                "FEISHU_FOLDER_ROUTE_KEYS=MAIN",
                "FEISHU_FOLDER_MAIN_NAME=main-route",
                "FEISHU_FOLDER_MAIN_TOKEN=ftok",
                "FEISHU_FOLDER_MAIN_QA_RULE_FILE=rules/q.md",
                "FEISHU_FOLDER_MAIN_DATASET_ID=ds1",
                "FEISHU_FOLDER_MAIN_DIFY_TARGET_KEY=DEFAULT",
                "CURSOR_RUN_TIMEOUT_SECONDS=3600",
                "DOC_RUNLOCK_TTL_SECONDS=10800",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("VLA_WORKSPACE_ROOT", str(ws))
    settings_mod.get_executor_settings.cache_clear()
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("FOLDER_ROUTES_FILE", str(bad_json))
    settings = ExecutorSettings()
    cfg = load_routing_config(settings)
    assert len(cfg.folder_routes) == 1
    assert cfg.folder_routes[0].dify_target_key == "DEFAULT"
    assert cfg.pipeline_workspace.path == str(ws.resolve())
    assert cfg.pipeline_workspace.cursor_timeout_seconds == 3600


def test_load_routing_json_fallback_without_route_keys(tmp_path, monkeypatch, caplog):
    ws = tmp_path / "json_ws"
    ws.mkdir()
    (ws / ".env").write_text(
        "DOC_RUNLOCK_TTL_SECONDS=10800\nCURSOR_RUN_TIMEOUT_SECONDS=7200\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("VLA_WORKSPACE_ROOT", str(ws))
    monkeypatch.delenv("FEISHU_FOLDER_ROUTE_KEYS", raising=False)
    settings_mod.get_executor_settings.cache_clear()

    routes_file = tmp_path / "routes.json"
    routes_file.write_text(
        json.dumps(
            {
                "pipeline_workspace": {
                    "path": "D:\\\\pipeline",
                    "cursor_timeout_seconds": 1234,
                },
                "folder_routes": [
                    {
                        "folder_token": "tok1",
                        "qa_rule_file": "rules/a.md",
                        "dataset_id": "ds",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    settings = ExecutorSettings(folder_routes_file=str(routes_file))
    cfg = load_routing_config(settings)
    assert cfg.folder_routes[0].dify_target_key == "DEFAULT"
    assert cfg.folder_routes[0].folder_token == "tok1"
    assert "legacy JSON" in caplog.text
