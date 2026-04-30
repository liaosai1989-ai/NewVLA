import json
import uuid

from fakeredis import FakeStrictRedis

from webhook_cursor_executor.models import DocumentSnapshot, RunContext
from rq.timeouts import JobTimeoutException

from webhook_cursor_executor.scheduler import (
    _LAUNCH_JOB_TIMEOUT_BUFFER_SECONDS,
    dataset_id_is_placeholder,
    finalize_document_run_job,
    launch_cursor_run_job,
    new_run_id,
    recover_stale_launch,
    schedule_document_job,
)
from webhook_cursor_executor.settings import ExecutorSettings
from webhook_cursor_executor.state_store import RedisStateStore


class FakeQueue:
    def __init__(self) -> None:
        self.calls = []

    def enqueue(self, job_name: str, **kwargs) -> None:
        self.calls.append((job_name, kwargs))


def test_dataset_id_is_placeholder_known_ids_and_prefix():
    assert dataset_id_is_placeholder("dataset_placeholder_replace_me")
    assert dataset_id_is_placeholder("placeholder:demo")
    assert not dataset_id_is_placeholder("8aa735a4-f8fc-46c8-9620-c8df159ddc8e")


def test_new_run_id_is_uuid4_and_unique():
    a, b = new_run_id(), new_run_id()
    assert uuid.UUID(a).version == 4
    assert uuid.UUID(b).version == 4
    assert a != b


def test_schedule_enqueues_launch_with_rq_job_timeout():
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
        ingest_kind="drive_file",
        resource_plane="drive_file",
    )
    store.save_snapshot(snapshot)

    schedule_document_job(
        document_id="doc_1",
        version=2,
        state_store=store,
        queue=queue,
        runlock_ttl_seconds=10800,
    )

    assert len(queue.calls) == 1
    job_name, kwargs = queue.calls[0]
    assert job_name == "launch_cursor_run_job"
    assert kwargs["document_id"] == "doc_1"
    assert kwargs["version"] == 2
    assert "run_id" in kwargs
    assert kwargs["job_timeout"] == 7200 + _LAUNCH_JOB_TIMEOUT_BUFFER_SECONDS


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
        ingest_kind="drive_file",
        resource_plane="drive_file",
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
        ingest_kind="drive_file",
        resource_plane="drive_file",
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
        ingest_kind="drive_file",
        resource_plane="drive_file",
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
        ingest_kind="drive_file",
        resource_plane="drive_file",
        dify_target_key="CUSTOM",
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
    assert saved_context["ingest_kind"] == "drive_file"
    assert saved_context["resource_plane"] == "drive_file"
    assert saved_context["dify_target_key"] == "CUSTOM"
    assert saved_context["dataset_id_is_placeholder"] is False
    assert saved_context["doc_type"] == "docx"
    assert store.load_run_context("run_1") is None


def test_launch_writes_task_context_doc_type_from_snapshot(monkeypatch, tmp_path):
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    queue = FakeQueue()
    snapshot = DocumentSnapshot(
        event_id="evt_1",
        document_id="doc_sh",
        folder_token="fld_team_a",
        event_type="drive.file.updated_v1",
        qa_rule_file="rules/team_a_qa.md",
        dataset_id="dataset_team_a",
        workspace_path=str(tmp_path),
        cursor_timeout_seconds=120,
        received_at="2026-04-26T10:00:00Z",
        version=1,
        ingest_kind="drive_file",
        resource_plane="drive_file",
        doc_type="sheet",
    )
    store.save_snapshot(snapshot)
    store.try_acquire_runlock(
        document_id="doc_sh",
        run_id="run_sh",
        ttl_seconds=10800,
    )
    settings = ExecutorSettings(
        cursor_cli_config_path=str(tmp_path / "cli-config.json"),
        cursor_run_timeout_seconds=7200,
    )
    monkeypatch.setattr(
        "webhook_cursor_executor.scheduler.ensure_max_mode_config",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "webhook_cursor_executor.scheduler.launch_cursor_agent",
        lambda **_: type(
            "R",
            (),
            {"exit_code": 0, "status": "succeeded", "summary": "ok"},
        )(),
    )
    launch_cursor_run_job(
        document_id="doc_sh",
        version=1,
        run_id="run_sh",
        state_store=store,
        queue=queue,
        settings=settings,
    )
    context_path = tmp_path / ".cursor_task" / "run_sh" / "task_context.json"
    saved = json.loads(context_path.read_text(encoding="utf-8"))
    assert saved["doc_type"] == "sheet"


def test_launch_task_context_placeholder_dataset(monkeypatch, tmp_path):
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    queue = FakeQueue()
    snapshot = DocumentSnapshot(
        event_id="evt_1",
        document_id="doc_ph",
        folder_token="fld_team_a",
        event_type="drive.file.updated_v1",
        qa_rule_file="rules/team_a_qa.md",
        dataset_id="dataset_placeholder_replace_me",
        workspace_path=str(tmp_path),
        cursor_timeout_seconds=120,
        received_at="2026-04-26T10:00:00Z",
        version=1,
        ingest_kind="drive_file",
        resource_plane="drive_file",
    )
    store.save_snapshot(snapshot)
    store.try_acquire_runlock(
        document_id="doc_ph",
        run_id="run_ph",
        ttl_seconds=10800,
    )
    settings = ExecutorSettings(
        cursor_cli_config_path=str(tmp_path / "cli-config.json"),
        cursor_run_timeout_seconds=7200,
    )
    monkeypatch.setattr(
        "webhook_cursor_executor.scheduler.ensure_max_mode_config",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "webhook_cursor_executor.scheduler.launch_cursor_agent",
        lambda **_: type(
            "R",
            (),
            {"exit_code": 0, "status": "succeeded", "summary": "ok"},
        )(),
    )
    launch_cursor_run_job(
        document_id="doc_ph",
        version=1,
        run_id="run_ph",
        state_store=store,
        queue=queue,
        settings=settings,
    )
    ctx = json.loads(
        (tmp_path / ".cursor_task" / "run_ph" / "task_context.json").read_text(
            encoding="utf-8"
        )
    )
    assert ctx["dataset_id_is_placeholder"] is True
    assert store.load_run_context("run_ph") is None


def test_launch_finalizes_when_runlock_not_owned(monkeypatch, tmp_path):
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
        ingest_kind="drive_file",
        resource_plane="drive_file",
    )
    store.save_snapshot(snapshot)
    store.try_acquire_runlock(
        document_id="doc_1",
        run_id="run_other",
        ttl_seconds=10800,
    )
    settings = ExecutorSettings(
        cursor_cli_config_path=str(tmp_path / "cli-config.json"),
        cursor_run_timeout_seconds=7200,
    )
    launch_cursor_run_job(
        document_id="doc_1",
        version=1,
        run_id="run_mine",
        state_store=store,
        queue=queue,
        settings=settings,
    )
    res = store.load_run_result("run_mine")
    assert res is not None
    assert res.status == "failed"
    assert "runlock_lost_or_not_owned_before_launch" in (res.summary or "")


def test_launch_rq_timeout_finalizes(monkeypatch, tmp_path):
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
        ingest_kind="drive_file",
        resource_plane="drive_file",
    )
    store.save_snapshot(snapshot)
    store.try_acquire_runlock(
        document_id="doc_1",
        run_id="run_to",
        ttl_seconds=10800,
    )
    settings = ExecutorSettings(
        cursor_cli_config_path=str(tmp_path / "cli-config.json"),
        cursor_run_timeout_seconds=7200,
    )
    monkeypatch.setattr(
        "webhook_cursor_executor.scheduler.ensure_max_mode_config",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "webhook_cursor_executor.scheduler.launch_cursor_agent",
        lambda **_: (_ for _ in ()).throw(JobTimeoutException("rq cut")),
    )
    launch_cursor_run_job(
        document_id="doc_1",
        version=1,
        run_id="run_to",
        state_store=store,
        queue=queue,
        settings=settings,
    )
    res = store.load_run_result("run_to")
    assert res.status == "failed"
    assert res.exit_code == 124
    assert "job_or_agent_timeout" in (res.summary or "")
    assert store.redis.get("webhook:doc:runlock:doc_1") is None


def test_recover_stale_launch_requeues_when_snapshot_ahead(tmp_path):
    store = RedisStateStore(redis_client=FakeStrictRedis(decode_responses=True))
    queue = FakeQueue()
    doc = "doc_stale"
    rid = "run_stale_1"
    snap = DocumentSnapshot(
        event_id="evt_new",
        document_id=doc,
        folder_token="fld_team_a",
        event_type="drive.file.edit_v1",
        qa_rule_file="rules/x.mdc",
        dataset_id="ds",
        workspace_path=str(tmp_path),
        cursor_timeout_seconds=300,
        received_at="2026-04-26T12:00:00Z",
        version=6,
        ingest_kind="drive_file",
        resource_plane="drive_file",
    )
    store.save_snapshot(snap)
    store.try_acquire_runlock(document_id=doc, run_id=rid, ttl_seconds=10800)
    store.mark_rerun(document_id=doc, target_version=6)
    store.save_run_context(
        RunContext(
            run_id=rid,
            document_id=doc,
            version=5,
            event_id="evt_old",
            workspace_path=str(tmp_path),
            status="running",
        )
    )
    assert recover_stale_launch(
        run_id=rid, state_store=store, queue=queue, summary="ops_cleanup"
    )
    assert store.load_run_result(rid).summary == "ops_cleanup"
    assert store.redis.get(f"webhook:doc:runlock:{doc}") is None
    assert queue.calls[-1] == (
        "schedule_document_job",
        {"document_id": doc, "version": 6},
    )
