from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from feishu_webhook.queue_rq import (
    build_rq_queue_from_settings,
    build_rq_redis,
    build_state_redis,
)
from feishu_webhook.settings import get_webhook_settings
from feishu_webhook.types import coerce_feishu_ingest_kind
from feishu_webhook.webhook_debounce import claim_debounce_and_clear

log = logging.getLogger(__name__)

DocumentJobHandler = Callable[
    [str, str, str | None, str | None, str | None],
    Any,
]

_document_job_handler: DocumentJobHandler | None = None


def configure_document_job_handler(handler: DocumentJobHandler) -> None:
    global _document_job_handler
    _document_job_handler = handler


def _require_handler() -> DocumentJobHandler:
    if _document_job_handler is None:
        raise RuntimeError(
            "document job handler is not configured; "
            "call configure_document_job_handler(...) during app startup"
        )
    return _document_job_handler


def process_document_job(
    document_id: str,
    event_id: str,
    folder_token: str | None = None,
    feishu_ingest_kind: str | None = None,
    feishu_file_type_hint: str | None = None,
) -> None:
    ingest = coerce_feishu_ingest_kind(feishu_ingest_kind)
    handler = _require_handler()

    log.info(
        "process_document_job start document_id=%s event_id=%s ingest=%s",
        document_id,
        event_id,
        ingest.value,
    )

    handler(
        document_id,
        event_id,
        folder_token,
        ingest.value,
        feishu_file_type_hint,
    )

    log.info(
        "process_document_job done document_id=%s event_id=%s",
        document_id,
        event_id,
    )


def flush_debounced_document_job(
    document_id: str,
    version: int,
) -> None:
    settings = get_webhook_settings()
    state_redis = build_state_redis(settings)
    rq_redis = build_rq_redis(settings)

    payload = claim_debounce_and_clear(state_redis, document_id, int(version))
    if payload is None:
        log.info(
            "debounce flush stale document_id=%s version=%s",
            document_id,
            version,
        )
        return

    event_id = str(payload.get("event_id") or "").strip()
    if not event_id:
        log.warning(
            "debounce flush missing event_id document_id=%s version=%s",
            document_id,
            version,
        )
        return

    raw_folder_token = payload.get("folder_token")
    folder_token = "" if raw_folder_token is None else str(raw_folder_token)

    raw_hint = payload.get("feishu_file_type_hint")
    file_type_hint = (
        str(raw_hint).strip()
        if raw_hint is not None and str(raw_hint).strip()
        else None
    )

    queue = build_rq_queue_from_settings(settings, rq_redis)
    queue.enqueue_document_job(
        document_id,
        event_id,
        folder_token,
        feishu_ingest_kind=payload.get("feishu_ingest_kind"),
        feishu_file_type_hint=file_type_hint,
    )

    log.info(
        "debounce flush applied document_id=%s event_id=%s version=%s",
        document_id,
        event_id,
        version,
    )

