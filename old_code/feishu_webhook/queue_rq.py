from __future__ import annotations

from datetime import timedelta

from redis import Redis
from rq import Queue

from feishu_webhook.settings import WebhookSettings
from feishu_webhook.types import FeishuIngestKind, coerce_feishu_ingest_kind


class RQQueueAdapter:
    def __init__(
        self,
        rq_redis_conn: Redis,
        queue_name: str,
        *,
        main_job_name: str = "feishu_webhook.worker_tasks.process_document_job",
        debounce_job_name: str = "feishu_webhook.worker_tasks.flush_debounced_document_job",
        job_timeout_seconds: int = 3600,
    ) -> None:
        self._q = Queue(queue_name, connection=rq_redis_conn)
        self._main_job_name = main_job_name
        self._debounce_job_name = debounce_job_name
        self._job_timeout_seconds = max(1, int(job_timeout_seconds))

    def enqueue_document_job(
        self,
        document_id: str,
        event_id: str,
        folder_token: str | None = None,
        *,
        feishu_ingest_kind: FeishuIngestKind | str = FeishuIngestKind.CLOUD_DOCX,
        feishu_file_type_hint: str | None = None,
    ):
        kind = coerce_feishu_ingest_kind(feishu_ingest_kind)
        hint = (feishu_file_type_hint or "").strip() or None
        return self._q.enqueue(
            self._main_job_name,
            document_id,
            event_id,
            folder_token,
            kind.value,
            hint,
            job_timeout=self._job_timeout_seconds,
        )

    def enqueue_debounce_flush(
        self,
        document_id: str,
        version: int,
        delay_seconds: int,
    ):
        return self._q.enqueue_in(
            timedelta(seconds=max(0, int(delay_seconds))),
            self._debounce_job_name,
            document_id,
            int(version),
            job_timeout=120,
        )


def build_state_redis(settings: WebhookSettings) -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def build_rq_redis(settings: WebhookSettings) -> Redis:
    return Redis.from_url(settings.redis_url)


def build_rq_queue_from_settings(
    settings: WebhookSettings,
    rq_redis_conn: Redis,
    *,
    main_job_name: str = "feishu_webhook.worker_tasks.process_document_job",
    debounce_job_name: str = "feishu_webhook.worker_tasks.flush_debounced_document_job",
) -> RQQueueAdapter:
    return RQQueueAdapter(
        rq_redis_conn,
        settings.vla_queue_name,
        main_job_name=main_job_name,
        debounce_job_name=debounce_job_name,
        job_timeout_seconds=settings.vla_rq_job_timeout_seconds,
    )

