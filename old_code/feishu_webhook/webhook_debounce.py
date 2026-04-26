"""Redis debounce helpers for last-write-wins document enqueue."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Protocol

from redis import Redis, WatchError

from feishu_webhook.types import FeishuIngestKind

log = logging.getLogger(__name__)


class DebounceQueuePort(Protocol):
    def enqueue_debounce_flush(
        self, document_id: str, version: int, delay_seconds: int
    ) -> Any:
        ...


def debounce_doc_key(document_id: str) -> str:
    return f"webhook:debounce:doc:{document_id}"


def debounce_ver_key(document_id: str) -> str:
    return f"webhook:debounce:ver:{document_id}"


def save_debounce_snapshot(
    redis_conn: Redis,
    document_id: str,
    payload: dict[str, Any],
    *,
    debounce_window_seconds: int,
) -> int:
    _ = debounce_window_seconds
    doc_key = debounce_doc_key(document_id)
    ver_key = debounce_ver_key(document_id)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    pipe = redis_conn.pipeline(transaction=True)
    pipe.set(doc_key, raw)
    pipe.incr(ver_key)
    _, ver_raw = pipe.execute()
    return int(ver_raw)


def claim_debounce_and_clear(
    redis_conn: Redis,
    document_id: str,
    version: int,
) -> dict[str, Any] | None:
    ver_key = debounce_ver_key(document_id)
    doc_key = debounce_doc_key(document_id)
    expected = int(version)

    doc_raw: str | bytes | None = None
    while True:
        doc_raw = None
        pipe = redis_conn.pipeline()
        try:
            pipe.watch(ver_key)
            current_raw = pipe.get(ver_key)
            if current_raw is None or int(current_raw) != expected:
                pipe.unwatch()
                return None
            doc_raw = pipe.get(doc_key)
            pipe.multi()
            pipe.delete(ver_key, doc_key)
            pipe.execute()
            break
        except WatchError:
            continue
        finally:
            pipe.reset()

    if doc_raw is None:
        return None
    if isinstance(doc_raw, bytes):
        doc_raw = doc_raw.decode("utf-8")
    if not isinstance(doc_raw, str) or not doc_raw.strip():
        return None
    try:
        out = json.loads(doc_raw)
    except json.JSONDecodeError:
        return None
    return out if isinstance(out, dict) else None


def build_webhook_debounce_payload(
    *,
    event_id: str,
    folder_token: str,
    event_type: str,
    feishu_ingest_kind: str = "cloud_docx",
    feishu_file_type_hint: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_id": event_id,
        "folder_token": folder_token,
        "event_type": event_type,
        "updated_unix": int(time.time()),
        "feishu_ingest_kind": feishu_ingest_kind,
    }
    if feishu_file_type_hint:
        payload["feishu_file_type_hint"] = feishu_file_type_hint
    return payload


def schedule_feishu_doc_enqueue_after_webhook(
    *,
    queue: DebounceQueuePort,
    redis_conn: Redis,
    doc_id: str,
    event_id: str,
    folder_token: str,
    event_type: str,
    ingest_kind: FeishuIngestKind,
    debounce_seconds: int,
    feishu_file_type_hint: str | None = None,
) -> None:
    hint = (feishu_file_type_hint or "").strip() or None
    payload = build_webhook_debounce_payload(
        event_id=event_id,
        folder_token=folder_token or "",
        event_type=event_type,
        feishu_ingest_kind=ingest_kind.value,
        feishu_file_type_hint=hint,
    )
    version = save_debounce_snapshot(
        redis_conn,
        doc_id,
        payload,
        debounce_window_seconds=int(debounce_seconds),
    )
    try:
        queue.enqueue_debounce_flush(doc_id, version, int(debounce_seconds))
    except Exception:
        try:
            redis_conn.delete(debounce_doc_key(doc_id), debounce_ver_key(doc_id))
        except Exception:
            log.exception("failed to clear debounce snapshot after enqueue error")
        raise

