from __future__ import annotations

import uuid
from pathlib import Path

from webhook_cursor_executor.cursor_cli import ensure_max_mode_config, launch_cursor_agent
from webhook_cursor_executor.models import RunContext, RunResult, TaskContext
from webhook_cursor_executor.task_files import write_task_bundle


def new_run_id() -> str:
    return f"run_{uuid.uuid4().hex[:12]}"


def schedule_document_job(
    *,
    document_id: str,
    version: int,
    state_store,
    queue,
    runlock_ttl_seconds: int,
) -> None:
    snapshot = state_store.load_snapshot(document_id)
    if snapshot is None or snapshot.version != version:
        return

    run_id = new_run_id()
    locked = state_store.try_acquire_runlock(
        document_id=document_id,
        run_id=run_id,
        ttl_seconds=runlock_ttl_seconds,
    )
    if not locked:
        state_store.mark_rerun(document_id=document_id, target_version=snapshot.version)
        return

    queue.enqueue(
        "launch_cursor_run_job",
        document_id=document_id,
        version=snapshot.version,
        run_id=run_id,
    )


def launch_cursor_run_job(
    *,
    document_id: str,
    version: int,
    run_id: str,
    state_store,
    queue,
    settings,
) -> None:
    snapshot = state_store.load_snapshot(document_id)
    if snapshot is None or snapshot.version != version:
        finalize_document_run_job(
            run_id=run_id,
            document_id=document_id,
            version=version,
            exit_code=1,
            status="failed",
            summary="snapshot_missing_or_stale",
            state_store=state_store,
            queue=queue,
        )
        return

    if not state_store.runlock_owned_by(document_id=document_id, run_id=run_id):
        return

    task_context = TaskContext(
        schema_version="1",
        run_id=run_id,
        event_id=snapshot.event_id,
        document_id=snapshot.document_id,
        folder_token=snapshot.folder_token,
        event_type=snapshot.event_type,
        snapshot_version=snapshot.version,
        qa_rule_file=snapshot.qa_rule_file,
        dataset_id=snapshot.dataset_id,
        workspace_path=snapshot.workspace_path,
        trigger_source="feishu_webhook",
        received_at=snapshot.received_at,
        cursor_timeout_seconds=snapshot.cursor_timeout_seconds,
    )
    bundle = write_task_bundle(
        workspace_path=Path(snapshot.workspace_path),
        run_id=run_id,
        context=task_context.model_dump(),
    )

    state_store.save_run_context(
        RunContext(
            run_id=run_id,
            document_id=document_id,
            version=version,
            event_id=snapshot.event_id,
            workspace_path=snapshot.workspace_path,
            status="running",
        )
    )

    try:
        ensure_max_mode_config(config_path=Path(settings.cursor_cli_config_path))
    except Exception as exc:
        finalize_document_run_job(
            run_id=run_id,
            document_id=document_id,
            version=version,
            exit_code=1,
            status="failed",
            summary=f"max_mode_sync_failed:{exc}",
            state_store=state_store,
            queue=queue,
        )
        return

    try:
        result = launch_cursor_agent(
            cwd=Path(snapshot.workspace_path),
            prompt_text=bundle.prompt_path.read_text(encoding="utf-8"),
            model=settings.cursor_cli_model,
            timeout_seconds=snapshot.cursor_timeout_seconds,
        )
    except FileNotFoundError as exc:
        finalize_document_run_job(
            run_id=run_id,
            document_id=document_id,
            version=version,
            exit_code=127,
            status="failed",
            summary=f"cursor_not_in_path:{exc}",
            state_store=state_store,
            queue=queue,
        )
        return

    queue.enqueue(
        "finalize_document_run_job",
        run_id=run_id,
        document_id=document_id,
        version=version,
        exit_code=result.exit_code,
        status=result.status,
        summary=result.summary,
    )


def finalize_document_run_job(
    *,
    run_id: str,
    document_id: str,
    version: int,
    exit_code: int,
    status: str,
    summary: str | None,
    state_store,
    queue,
) -> None:
    state_store.save_run_result(
        RunResult(
            run_id=run_id,
            document_id=document_id,
            version=version,
            exit_code=exit_code,
            status=status,
            summary=summary,
        )
    )
    state_store.clear_run_context(run_id)
    state_store.release_runlock(document_id=document_id, run_id=run_id)

    rerun = state_store.get_rerun(document_id)
    latest_snapshot = state_store.load_snapshot(document_id)
    if rerun is None or latest_snapshot is None:
        state_store.clear_rerun(document_id)
        return
    if rerun.target_version <= version:
        state_store.clear_rerun(document_id)
        return

    state_store.clear_rerun(document_id)
    queue.enqueue(
        "schedule_document_job",
        document_id=document_id,
        version=latest_snapshot.version,
    )
