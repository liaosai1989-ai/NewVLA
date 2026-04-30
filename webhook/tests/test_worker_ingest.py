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
from webhook_cursor_executor.worker import (
    flush_debounced_feishu_ingest_entry,
    ingest_feishu_document_event_entry,
)


class _CapQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.in_calls: list[tuple[object, str, dict]] = []

    def enqueue(self, job_name: str, **kwargs) -> None:
        self.calls.append((job_name, kwargs))

    def enqueue_in(self, time_delta, job_name: str, **kwargs) -> None:
        self.in_calls.append((time_delta, job_name, kwargs))


def test_ingest_resolves_listing_marks_snapshot_schedules():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
        feishu_ingest_debounce_seconds=0,
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
                    ingest_kind="drive_file",
                    doc_type="sheet",
                )
    assert store.try_mark_event_seen("ev1") is False
    assert cap.calls[0][0] == "schedule_document_job"
    assert cap.calls[0][1]["document_id"] == "doc1"
    sn = store.load_snapshot("doc1")
    assert sn is not None
    assert sn.folder_token == "fld_team_a"
    assert sn.ingest_kind == "drive_file"
    assert sn.resource_plane == "drive_file"
    assert sn.dify_target_key == "DEFAULT"
    assert sn.doc_type == "sheet"


def test_ingest_duplicate_event_skips_second_schedule():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
        feishu_ingest_debounce_seconds=0,
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
                    ingest_kind="drive_file",
                )
                ingest_feishu_document_event_entry(
                    event_id="dup1",
                    document_id="d1",
                    event_type="t",
                    folder_token="",
                    ingest_kind="drive_file",
                )
    sched = [c for c in cap.calls if c[0] == "schedule_document_job"]
    assert sched == [("schedule_document_job", {"document_id": "d1", "version": 1})]


def test_ingest_debounce_two_events_one_flush_schedules_once():
    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
        feishu_ingest_debounce_seconds=90,
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
                    event_id="ev_first",
                    document_id="d1",
                    event_type="t",
                    folder_token="",
                    ingest_kind="drive_file",
                )
                ingest_feishu_document_event_entry(
                    event_id="ev_second",
                    document_id="d1",
                    event_type="t",
                    folder_token="",
                    ingest_kind="drive_file",
                )
    sched_immediate = [c for c in cap.calls if c[0] == "schedule_document_job"]
    assert sched_immediate == []
    assert len(cap.in_calls) == 2
    assert cap.in_calls[0][1] == "flush_debounced_feishu_ingest"
    assert cap.in_calls[1][1] == "flush_debounced_feishu_ingest"

    stale = cap.in_calls[0][2]["token"]
    flush_debounced_feishu_ingest_entry(document_id="d1", token=stale)
    assert [c for c in cap.calls if c[0] == "schedule_document_job"] == []

    latest = cap.in_calls[1][2]["token"]
    with patch("webhook_cursor_executor.worker.build_worker_runtime") as br2:
        br2.return_value = (settings, store, cap)
        flush_debounced_feishu_ingest_entry(document_id="d1", token=latest)
    sched = [c for c in cap.calls if c[0] == "schedule_document_job"]
    assert sched == [("schedule_document_job", {"document_id": "d1", "version": 1})]
    sn = store.load_snapshot("d1")
    assert sn is not None
    assert sn.event_id == "ev_second"


def test_ingest_created_in_folder_triggers_per_doc_subscribe(monkeypatch):
    sub: list[tuple[str, str]] = []

    def capture(settings, doc_id, ft):
        sub.append((doc_id, ft))

    settings = ExecutorSettings(
        feishu_encrypt_key="",
        feishu_verification_token="",
        feishu_ingest_debounce_seconds=0,
        feishu_app_id="a",
        feishu_app_secret="b",
    )
    routing = RoutingConfig(
        pipeline_workspace=PipelineWorkspace(
            path="C:\\workspaces\\pipeline",
            cursor_timeout_seconds=7200,
        ),
        folder_routes=[
            FolderRoute(
                folder_token="fld_team_a",
                qa_rule_file="team_a.md",
                dataset_id="ds1",
            )
        ],
    )
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    cap = _CapQueue()
    monkeypatch.setattr(
        "webhook_cursor_executor.worker.event_driven_per_doc_subscribe",
        capture,
    )
    with patch("webhook_cursor_executor.worker.build_worker_runtime") as br:
        br.return_value = (settings, store, cap)
        with patch("webhook_cursor_executor.worker.load_routing_config", lambda s: routing):
            with patch(
                "webhook_cursor_executor.worker.resolve_folder_token_by_listing",
                lambda **k: "fld_team_a",
            ):
                ingest_feishu_document_event_entry(
                    event_id="ev_cif",
                    document_id="new_t",
                    event_type="drive.file.created_in_folder_v1",
                    folder_token="",
                    ingest_kind="cloud_docx",
                    doc_type=None,
                    drive_subscribe_file_type="docx",
                )
    assert sub == [("new_t", "docx")]
    assert cap.calls[0][0] == "schedule_document_job"
