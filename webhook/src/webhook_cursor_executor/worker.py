from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from redis import Redis
from rq import Queue
from rq.timeouts import JobTimeoutException

from webhook_cursor_executor.feishu_drive_subscribe import (
    CREATED_IN_FOLDER_V1,
    DRIVE_SUBSCRIBE_FILE_TYPES,
    event_driven_per_doc_subscribe,
    subscribe_file_type_fallback,
)
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

    def enqueue_in(self, time_delta: timedelta, job_name: str, **kwargs) -> None:
        self.queue.enqueue_in(
            time_delta,
            f"webhook_cursor_executor.worker.{job_name}_entry",
            **kwargs,
        )


def build_worker_runtime():
    settings = get_executor_settings()
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    store = RedisStateStore(redis_client=redis_client)
    queue = RQQueueAdapter(queue=Queue(settings.vla_queue_name, connection=redis_client))
    return settings, store, queue


def _ingest_payload_dict(
    *,
    event_id: str,
    document_id: str,
    event_type: str,
    ingest_kind: str,
    folder_token: str,
    routing_config,
    route,
    doc_type: str | None = None,
    resource_plane: str = "drive_file",
) -> dict[str, object]:
    out: dict[str, object] = {
        "event_id": event_id,
        "document_id": document_id,
        "event_type": event_type,
        "ingest_kind": ingest_kind,
        "folder_token": folder_token,
        "workspace_path": routing_config.pipeline_workspace.path,
        "cursor_timeout_seconds": routing_config.pipeline_workspace.cursor_timeout_seconds,
        "qa_rule_file": route.qa_rule_file,
        "dataset_id": route.dataset_id,
        "dify_target_key": route.dify_target_key,
        "resource_plane": resource_plane,
    }
    if doc_type is not None:
        out["doc_type"] = doc_type
    return out


def _commit_ingest_from_payload(
    *,
    store: RedisStateStore,
    queue: RQQueueAdapter,
    payload: dict[str, object],
) -> None:
    document_id = str(payload["document_id"])
    version = store.next_version(document_id)
    raw_dt = payload.get("doc_type")
    doc_type_val: str | None
    if raw_dt is None:
        doc_type_val = None
    else:
        s = str(raw_dt).strip()
        doc_type_val = s if s else None
    snapshot = DocumentSnapshot(
        event_id=str(payload["event_id"]),
        document_id=document_id,
        folder_token=str(payload["folder_token"]),
        event_type=str(payload["event_type"]),
        qa_rule_file=str(payload["qa_rule_file"]),
        dataset_id=str(payload["dataset_id"]),
        workspace_path=str(payload["workspace_path"]),
        cursor_timeout_seconds=int(payload["cursor_timeout_seconds"]),
        received_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        version=version,
        dify_target_key=str(payload["dify_target_key"]),
        ingest_kind=str(payload["ingest_kind"]),
        resource_plane=str(
            payload.get("resource_plane")
            or (
                "cloud_docx" if str(payload["ingest_kind"]) == "cloud_docx" else "drive_file"
            )
        ),
        doc_type=doc_type_val,
    )
    store.save_snapshot(snapshot)
    queue.enqueue("schedule_document_job", document_id=document_id, version=version)


def flush_debounced_feishu_ingest_entry(*, document_id: str, token: str) -> None:
    """debounce 窗口结束后合并为一次 next_version + snapshot + schedule。"""
    _, store, queue = build_worker_runtime()
    raw = store.take_ingest_debounce_payload_if_token(document_id=document_id, token=token)
    if raw is None:
        logger.info("ingest_debounce_flush_superseded document_id=%s", document_id)
        return
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        logger.error("ingest_debounce_payload_invalid document_id=%s", document_id)
        return
    _commit_ingest_from_payload(store=store, queue=queue, payload=payload)


def ingest_feishu_document_event_entry(
    *,
    event_id: str,
    document_id: str,
    event_type: str,
    ingest_kind: str,
    folder_token: str = "",
    doc_type: str | None = None,
    resource_plane: str | None = None,
    drive_subscribe_file_type: str | None = None,
) -> None:
    """无 folder_token 的事件在 HTTP 中只入队；此处列目录解析路由并落快照，再 schedule。"""
    settings, store, queue = build_worker_runtime()
    routing_config = load_routing_config(settings)
    rp = (resource_plane or "").strip() or (
        "cloud_docx" if ingest_kind == "cloud_docx" else "drive_file"
    )
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
    if event_type == CREATED_IN_FOLDER_V1:
        sub_ft = (drive_subscribe_file_type or "").strip().lower()
        if sub_ft not in DRIVE_SUBSCRIBE_FILE_TYPES:
            sub_ft = subscribe_file_type_fallback(ingest_kind, doc_type) or ""
        if sub_ft in DRIVE_SUBSCRIBE_FILE_TYPES:
            event_driven_per_doc_subscribe(settings, document_id, sub_ft)
    if not store.try_mark_event_seen(event_id):
        return
    payload = _ingest_payload_dict(
        event_id=event_id,
        document_id=document_id,
        event_type=event_type,
        ingest_kind=ingest_kind,
        folder_token=ft,
        routing_config=routing_config,
        route=route,
        doc_type=doc_type,
        resource_plane=rp,
    )
    debounce = settings.feishu_ingest_debounce_seconds
    if debounce <= 0:
        _commit_ingest_from_payload(store=store, queue=queue, payload=payload)
        return
    flush_token = str(uuid.uuid4())
    store.write_ingest_debounce(
        document_id=document_id,
        token=flush_token,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )
    queue.enqueue_in(
        timedelta(seconds=debounce),
        "flush_debounced_feishu_ingest",
        document_id=document_id,
        token=flush_token,
    )


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
    try:
        launch_cursor_run_job(
            document_id=document_id,
            version=version,
            run_id=run_id,
            state_store=store,
            queue=queue,
            settings=settings,
        )
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        ctx = store.load_run_context(run_id)
        if ctx is not None:
            exit_code = 124 if isinstance(exc, JobTimeoutException) else 1
            finalize_document_run_job(
                run_id=run_id,
                document_id=document_id,
                version=version,
                exit_code=exit_code,
                status="failed",
                summary=f"launch_entry_uncaught:{type(exc).__name__}:{exc!s}"[:800],
                state_store=store,
                queue=queue,
            )
        raise


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
