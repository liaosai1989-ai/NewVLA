from __future__ import annotations

from redis import Redis
from rq import Queue

from webhook_cursor_executor.scheduler import (
    finalize_document_run_job,
    launch_cursor_run_job,
    schedule_document_job,
)
from webhook_cursor_executor.settings import get_executor_settings
from webhook_cursor_executor.state_store import RedisStateStore


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
