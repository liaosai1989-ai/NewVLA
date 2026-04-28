import json

from webhook_cursor_executor.task_files import write_task_bundle


def test_write_task_bundle_uses_run_dir(tmp_path):
    context = {
        "schema_version": "1",
        "run_id": "run_001",
        "event_id": "evt_1",
        "document_id": "doc_1",
        "folder_token": "fld_team_a",
        "event_type": "drive.file.updated_v1",
        "snapshot_version": 3,
        "qa_rule_file": "rules/team_a_qa.md",
        "dataset_id": "dataset_team_a",
        "workspace_path": str(tmp_path),
        "trigger_source": "feishu_webhook",
        "received_at": "2026-04-26T10:00:00Z",
        "cursor_timeout_seconds": 7200,
        "ingest_kind": "drive_file",
        "dify_target_key": "DEFAULT",
        "dataset_id_is_placeholder": False,
    }

    bundle = write_task_bundle(workspace_path=tmp_path, run_id="run_001", context=context)
    saved = json.loads(bundle.context_path.read_text(encoding="utf-8"))
    prompt = bundle.prompt_path.read_text(encoding="utf-8")

    assert bundle.outputs_dir.is_dir()
    assert ".cursor_task/run_001" in str(bundle.context_path).replace("\\", "/")
    assert saved["dataset_id"] == "dataset_team_a"
    assert "dify_target_key" in prompt and "ingest_kind" in prompt
    assert "dataset_id_is_placeholder" in prompt
    assert "CSV" in prompt or "校验" in prompt
