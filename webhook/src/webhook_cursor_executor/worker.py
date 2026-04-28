from __future__ import annotations

import logging
from datetime import datetime, timezone

from redis import Redis
from rq import Queue

from webhook_cursor_executor.feishu_folder_resolve import (
    resolve_folder_route,
    resolve_folder_token_by_listing,
)
from webhook_cursor_executor.models import DocumentSnapshot
from webhook_cursor_executor.scheduler import (
    finalize_document_run_job,
    launch_cursor_run_job,
    schedule_document_job,
)
from webhook_cursor_executor.settings import get_executor_settings, load_routing_config
from webhook_cursor_executor.state_store import RedisStateStore

logger = logging.getLogger(__name__)


class RQQueueAdapter:
    def __init__(self, *, queue: Queue) -> None:
        self.queue = queue

    def enqueue(self, job_name: str, **kwargs) -> None:
        self.queue.enqueue(f"webhook_cursor_executor.worker.{job_name}_entry", **kwargs)


def build_worker_runtime():
    settings = get_executor_settings()
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    store = RedisStateStore(redis_client=redis_client)
    queue = RQQueueAdapter(queue=Queue(settings.vla_queue_name, connection=redis_client))
    return settings, store, queue


def ingest_feishu_document_event_entry(
    *,
    event_id: str,
    document_id: str,
    event_type: str,
    ingest_kind: str,
    folder_token: str = "",
) -> None:
    """无 folder_token 的事件在 HTTP 中只入队；此处列目录解析路由并落快照，再 schedule。"""
    settings, store, queue = build_worker_runtime()
    routing_config = load_routing_config(settings)
    ft = (folder_token or "").strip()
    if not ft:
        listed = resolve_folder_token_by_listing(
            routing_config=routing_config,
            file_token=document_id,
            settings=settings,
        )
        if listed:
            ft = listed
    route = resolve_folder_route(routing_config, ft)
    if route is None:
        logger.warning(
            "ingest_skipped_no_route event_id=%s document_id=%s folder_token=%s",
            event_id,
            document_id,
            ft or "(empty)",
        )
        return
    if not store.try_mark_event_seen(event_id):
        return
    version = store.next_version(document_id)
    snapshot = DocumentSnapshot(
        event_id=event_id,
        document_id=document_id,
        folder_token=ft,
        event_type=event_type,
        qa_rule_file=route.qa_rule_file,
        dataset_id=route.dataset_id,
        workspace_path=routing_config.pipeline_workspace.path,
        cursor_timeout_seconds=routing_config.pipeline_workspace.cursor_timeout_seconds,
        received_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        version=version,
        dify_target_key=route.dify_target_key,
        ingest_kind=ingest_kind,
    )
    store.save_snapshot(snapshot)
    queue.enqueue("schedule_document_job", document_id=document_id, version=version)


def schedule_document_job_entry(*, document_id: str, version: int) -> None:
    settings, store, queue = build_worker_runtime()
    schedule_document_job(
        document_id=document_id,
        version=version,
        state_store=store,
        queue=queue,
        runlock_ttl_seconds=settings.doc_runlock_ttl_seconds,
    )


def launch_cursor_run_job_entry(*, document_id: str, version: int, run_id: str) -> None:
    settings, store, queue = build_worker_runtime()
    launch_cursor_run_job(
        document_id=document_id,
        version=version,
        run_id=run_id,
        state_store=store,
        queue=queue,
        settings=settings,
    )


def finalize_document_run_job_entry(
    *,
    run_id: str,
    document_id: str,
    version: int,
    exit_code: int,
    status: str,
    summary: str | None = None,
) -> None:
    _, store, queue = build_worker_runtime()
    finalize_document_run_job(
        run_id=run_id,
        document_id=document_id,
        version=version,
        exit_code=exit_code,
        status=status,
        summary=summary,
        state_store=store,
        queue=queue,
    )
