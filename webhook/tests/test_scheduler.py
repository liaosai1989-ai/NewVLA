import json

from fakeredis import FakeStrictRedis

from webhook_cursor_executor.models import DocumentSnapshot
from webhook_cursor_executor.scheduler import (
    finalize_document_run_job,
    launch_cursor_run_job,
    schedule_document_job,
)
from webhook_cursor_executor.settings import ExecutorSettings
from webhook_cursor_executor.state_store import RedisStateStore


class FakeQueue:
    def __init__(self) -> None:
        self.calls = []

    def enqueue(self, job_name: str, **kwargs) -> None:
        self.calls.append((job_name, kwargs))


def test_schedule_marks_rerun_when_busy():
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    queue = FakeQueue()
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
        version=2,
    )
    store.save_snapshot(snapshot)
    store.try_acquire_runlock(
        document_id="doc_1",
        run_id="run_existing",
        ttl_seconds=10800,
    )

    schedule_document_job(
        document_id="doc_1",
        version=2,
        state_store=store,
        queue=queue,
        runlock_ttl_seconds=10800,
    )

    assert store.get_rerun("doc_1").target_version == 2
    assert queue.calls == []


def test_finalize_saves_result_and_requeues_newer_version():
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    queue = FakeQueue()
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
        version=6,
    )
    store.save_snapshot(snapshot)
    store.mark_rerun(document_id="doc_1", target_version=6)

    finalize_document_run_job(
        run_id="run_1",
        document_id="doc_1",
        version=5,
        exit_code=0,
        status="succeeded",
        summary="ok",
        state_store=store,
        queue=queue,
    )

    assert store.load_run_result("run_1").status == "succeeded"
    assert queue.calls == [("schedule_document_job", {"document_id": "doc_1", "version": 6})]


def test_launch_fails_fast_when_max_mode_sync_fails(monkeypatch, tmp_path):
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    queue = FakeQueue()
    snapshot = DocumentSnapshot(
        event_id="evt_1",
        document_id="doc_1",
        folder_token="fld_team_a",
        event_type="drive.file.updated_v1",
        qa_rule_file="rules/team_a_qa.md",
        dataset_id="dataset_team_a",
        workspace_path=str(tmp_path),
        cursor_timeout_seconds=300,
        received_at="2026-04-26T10:00:00Z",
        version=1,
    )
    store.save_snapshot(snapshot)
    store.try_acquire_runlock(
        document_id="doc_1",
        run_id="run_1",
        ttl_seconds=10800,
    )
    settings = ExecutorSettings(
        cursor_cli_config_path=str(tmp_path / "cli-config.json"),
        cursor_run_timeout_seconds=7200,
    )

    monkeypatch.setattr(
        "webhook_cursor_executor.scheduler.ensure_max_mode_config",
        lambda **_: (_ for _ in ()).throw(OSError("locked")),
    )

    launch_cursor_run_job(
        document_id="doc_1",
        version=1,
        run_id="run_1",
        state_store=store,
        queue=queue,
        settings=settings,
    )

    assert store.load_run_result("run_1").status == "failed"


def test_launch_uses_workspace_timeout_in_task_context(monkeypatch, tmp_path):
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    queue = FakeQueue()
    snapshot = DocumentSnapshot(
        event_id="evt_1",
        document_id="doc_1",
        folder_token="fld_team_a",
        event_type="drive.file.updated_v1",
        qa_rule_file="rules/team_a_qa.md",
        dataset_id="dataset_team_a",
        workspace_path=str(tmp_path),
        cursor_timeout_seconds=321,
        received_at="2026-04-26T10:00:00Z",
        version=1,
    )
    store.save_snapshot(snapshot)
    store.try_acquire_runlock(
        document_id="doc_1",
        run_id="run_1",
        ttl_seconds=10800,
    )
    settings = ExecutorSettings(
        cursor_cli_config_path=str(tmp_path / "cli-config.json"),
        cursor_run_timeout_seconds=7200,
    )
    captured: dict[str, int] = {}

    monkeypatch.setattr(
        "webhook_cursor_executor.scheduler.ensure_max_mode_config",
        lambda **_: None,
    )

    def fake_launch_cursor_agent(**kwargs):
        captured["timeout_seconds"] = kwargs["timeout_seconds"]
        return type(
            "Result",
            (),
            {"exit_code": 0, "status": "succeeded", "summary": "ok"},
        )()

    monkeypatch.setattr(
        "webhook_cursor_executor.scheduler.launch_cursor_agent",
        fake_launch_cursor_agent,
    )

    launch_cursor_run_job(
        document_id="doc_1",
        version=1,
        run_id="run_1",
        state_store=store,
        queue=queue,
        settings=settings,
    )

    context_path = tmp_path / ".cursor_task" / "run_1" / "task_context.json"
    saved_context = json.loads(context_path.read_text(encoding="utf-8"))

    assert captured["timeout_seconds"] == 321
    assert saved_context["cursor_timeout_seconds"] == 321
