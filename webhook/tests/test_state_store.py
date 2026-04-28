import json

from fakeredis import FakeStrictRedis

from webhook_cursor_executor.models import DocumentSnapshot, RunResult
from webhook_cursor_executor.state_store import RedisStateStore


def test_event_seen_snapshot_and_run_result_roundtrip():
    redis_client = FakeStrictRedis(decode_responses=True)
    store = RedisStateStore(redis_client=redis_client)

    assert store.try_mark_event_seen("evt_1") is True
    assert store.try_mark_event_seen("evt_1") is False

    snapshot = DocumentSnapshot(
        event_id="evt_1",
        document_id="doc_1",
        folder_token="fld_team_a",
        event_type="drive.file.updated_v1",
        qa_rule_file="rules/team_a_qa.md",
        dataset_id="dataset_team_a",
        workspace_path="C:\\workspaces\\pipeline",
        cursor_timeout_seconds=7200,
        received_at="2026-04-26T10:00:00Z",
        version=3,
        ingest_kind="drive_file",
    )
    store.save_snapshot(snapshot)
    store.save_run_result(
        RunResult(
            run_id="run_1",
            document_id="doc_1",
            version=3,
            exit_code=0,
            status="succeeded",
            summary="ok",
        )
    )

    assert store.load_snapshot("doc_1").version == 3
    assert store.load_run_result("run_1").status == "succeeded"


def test_load_snapshot_returns_none_when_ingest_kind_missing():
    redis_client = FakeStrictRedis(decode_responses=True)
    store = RedisStateStore(redis_client=redis_client)
    doc_id = "legacy_no_ingest"
    legacy = {
        "event_id": "e1",
        "document_id": doc_id,
        "folder_token": "f1",
        "event_type": "drive.file.updated_v1",
        "qa_rule_file": "r.md",
        "dataset_id": "ds",
        "workspace_path": "C:\\ws",
        "cursor_timeout_seconds": 7200,
        "received_at": "2026-01-01T00:00:00Z",
        "version": 1,
    }
    redis_client.set(
        store._snapshot_key(doc_id),
        json.dumps(legacy),
        ex=store.snapshot_ttl_seconds,
    )
    assert store.load_snapshot(doc_id) is None


def test_load_snapshot_injects_default_dify_target_key_when_missing():
    redis_client = FakeStrictRedis(decode_responses=True)
    store = RedisStateStore(redis_client=redis_client)
    doc_id = "legacy_no_dify_key"
    body = {
        "event_id": "e1",
        "document_id": doc_id,
        "folder_token": "f1",
        "event_type": "drive.file.updated_v1",
        "qa_rule_file": "r.md",
        "dataset_id": "ds",
        "workspace_path": "C:\\ws",
        "cursor_timeout_seconds": 7200,
        "received_at": "2026-01-01T00:00:00Z",
        "version": 1,
        "ingest_kind": "drive_file",
    }
    redis_client.set(
        store._snapshot_key(doc_id),
        json.dumps(body),
        ex=store.snapshot_ttl_seconds,
    )
    sn = store.load_snapshot(doc_id)
    assert sn is not None
    assert sn.dify_target_key == "DEFAULT"
