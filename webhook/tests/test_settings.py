from webhook_cursor_executor.settings import ExecutorSettings, load_routing_config


def test_settings_defaults_and_route_loading(tmp_path):
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
