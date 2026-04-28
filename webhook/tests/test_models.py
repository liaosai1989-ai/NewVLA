import pytest
from pydantic import ValidationError

from webhook_cursor_executor.models import DocumentSnapshot, TaskContext


def test_document_snapshot_allows_default_dify_target_for_legacy_json():
    s = DocumentSnapshot.model_validate(
        {
            "event_id": "e1",
            "document_id": "d1",
            "folder_token": "f1",
            "event_type": "drive.file.edit_v1",
            "qa_rule_file": "rules/a.md",
            "dataset_id": "ds",
            "workspace_path": "C:\\ws",
            "cursor_timeout_seconds": 7200,
            "received_at": "2026-04-28T00:00:00+00:00",
            "version": 1,
            "ingest_kind": "drive_file",
        }
    )
    assert s.dify_target_key == "DEFAULT"


def test_task_context_requires_ingest_kind_and_dify_target_key():
    base = dict(
        schema_version="1",
        run_id="run_x",
        event_id="e1",
        document_id="d1",
        folder_token="f1",
        event_type="drive.file.edit_v1",
        snapshot_version=1,
        qa_rule_file="rules/a.md",
        dataset_id="ds",
        workspace_path="C:\\ws",
        trigger_source="feishu_webhook",
        received_at="2026-04-28T00:00:00+00:00",
        cursor_timeout_seconds=7200,
        ingest_kind="drive_file",
        dify_target_key="DEFAULT",
    )
    TaskContext.model_validate({**base, "dataset_id_is_placeholder": False})
    bad = {k: v for k, v in base.items() if k != "ingest_kind"}
    with pytest.raises(ValidationError):
        TaskContext.model_validate(bad)
