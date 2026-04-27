"""ingest_feishu_document_event_entry：无 folder_token 时 worker 内列目录 + 走 schedule 链。"""

from unittest.mock import patch

from fakeredis import FakeStrictRedis

from webhook_cursor_executor.settings import (
    ExecutorSettings,
    FolderRoute,
    PipelineWorkspace,
    RoutingConfig,
)
from webhook_cursor_executor.state_store import RedisStateStore
from webhook_cursor_executor.worker import ingest_feishu_document_event_entry


class _CapQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def enqueue(self, job_name: str, **kwargs) -> None:
        self.calls.append((job_name, kwargs))


def test_ingest_resolves_listing_marks_snapshot_schedules():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
    )
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_team_a",
                qa_rule_file="rules/team_a.md",
                dataset_id="ds1",
            )
        ],
    )
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    cap = _CapQueue()
    with patch("webhook_cursor_executor.worker.build_worker_runtime") as br:
        br.return_value = (settings, store, cap)
        with patch("webhook_cursor_executor.worker.load_routing_config", lambda s: routing):
            with patch(
                "webhook_cursor_executor.worker.resolve_folder_token_by_listing",
                lambda **k: "fld_team_a",
            ):
                ingest_feishu_document_event_entry(
                    event_id="ev1",
                    document_id="doc1",
                    event_type="drive.file.edit_v1",
                    folder_token="",
                )
    assert store.try_mark_event_seen("ev1") is False
    assert cap.calls[0][0] == "schedule_document_job"
    assert cap.calls[0][1]["document_id"] == "doc1"
    sn = store.load_snapshot("doc1")
    assert sn is not None
    assert sn.folder_token == "fld_team_a"


def test_ingest_duplicate_event_skips_second_schedule():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
    )
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_a",
                qa_rule_file="r.md",
                dataset_id="d",
            )
        ],
    )
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    cap = _CapQueue()
    with patch("webhook_cursor_executor.worker.build_worker_runtime") as br:
        br.return_value = (settings, store, cap)
        with patch("webhook_cursor_executor.worker.load_routing_config", lambda s: routing):
            with patch(
                "webhook_cursor_executor.worker.resolve_folder_token_by_listing",
                lambda **k: "fld_a",
            ):
                ingest_feishu_document_event_entry(
                    event_id="dup1",
                    document_id="d1",
                    event_type="t",
                    folder_token="",
                )
                ingest_feishu_document_event_entry(
                    event_id="dup1",
                    document_id="d1",
                    event_type="t",
                    folder_token="",
                )
    sched = [c for c in cap.calls if c[0] == "schedule_document_job"]
    assert sched == [("schedule_document_job", {"document_id": "d1", "version": 1})]
