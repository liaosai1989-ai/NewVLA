from __future__ import annotations

import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis import Redis
from rq import Queue

from webhook_cursor_executor.drive_doc_type import normalize_drive_doc_type
from webhook_cursor_executor.feishu_drive_subscribe import (
    maybe_per_doc_subscribe_on_created_in_folder,
    resolve_subscribe_file_type_for_created_in_folder,
)
from webhook_cursor_executor.feishu_resource_plane import resolve_drive_file_ingest
from webhook_cursor_executor.ingest_kind import derive_ingest_kind
from webhook_cursor_executor.models import DocumentSnapshot
from webhook_cursor_executor.settings import (
    ExecutorSettings,
    RoutingConfig,
    get_executor_settings,
    load_routing_config,
)
from webhook_cursor_executor.feishu_folder_resolve import resolve_folder_route
from webhook_cursor_executor.state_store import RedisStateStore
from webhook_cursor_executor.worker import RQQueueAdapter


def verify_signature(
    timestamp: str,
    nonce: str,
    encrypt_key: str,
    body: bytes,
    signature: str,
) -> bool:
    if not encrypt_key:
        return True
    digest = hashlib.sha256(f"{timestamp}{nonce}{encrypt_key}".encode("utf-8") + body)
    return digest.hexdigest() == signature


def parse_request_body(encrypt_key: str, body: bytes) -> dict[str, Any]:
    data = json.loads(body.decode("utf-8"))
    if "encrypt" not in data or not encrypt_key:
        return data
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    raw = base64.b64decode(data["encrypt"])
    iv, ciphertext = raw[:16], raw[16:]
    plaintext = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ciphertext), AES.block_size)
    return json.loads(plaintext.decode("utf-8"))


def verification_token_ok(
    payload: dict[str, Any],
    settings: ExecutorSettings,
) -> bool:
    expected = settings.feishu_verification_token.strip()
    if not expected:
        return True

    header = payload.get("header") or {}
    token = header.get("token") if isinstance(header.get("token"), str) else None
    if token is None and isinstance(payload.get("token"), str):
        token = payload.get("token")
    return token == expected


class InlineQueue:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def enqueue(self, job_name: str, **kwargs) -> None:
        self.calls.append((job_name, kwargs))


def create_app(
    *,
    settings: ExecutorSettings,
    routing_config: RoutingConfig,
    state_store: RedisStateStore,
    queue,
) -> FastAPI:
    app = FastAPI(title="Webhook Cursor Executor", version="0.1.0")

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"}, status_code=200)

    @app.get("/oauth/callback")
    async def oauth_callback(request: Request) -> JSONResponse:
        """浏览器 OAuth 回调（协作者用户授权）。与事件 webhook 路径无关。"""
        q = request.query_params
        err = (q.get("error") or "").strip()
        if err:
            return JSONResponse(
                {
                    "error": err,
                    "error_description": (q.get("error_description") or "").strip(),
                },
                status_code=400,
            )
        code = (q.get("code") or "").strip()
        state = (q.get("state") or "").strip()
        return JSONResponse(
            {
                "ok": True,
                "code": code or None,
                "state": state or None,
                "hint": (
                    "复制 code 后：py feishu_delegate_oauth_helper.py exchange --code <code> "
                    "（与 print-url 同一脚本路径旁的 .env）"
                ),
            }
        )

    @app.post(settings.feishu_webhook_path)
    async def feishu_webhook(request: Request) -> JSONResponse:
        raw = await request.body()
        try:
            payload = parse_request_body(settings.feishu_encrypt_key, raw)
        except (
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return JSONResponse({"error": "bad body"}, status_code=400)

        if payload.get("type") == "url_verification" and "challenge" in payload:
            if not verification_token_ok(payload, settings):
                return JSONResponse(
                    {"error": "invalid verification token"},
                    status_code=403,
                )
            return JSONResponse({"challenge": str(payload["challenge"])})

        timestamp = request.headers.get("X-Lark-Request-Timestamp", "")
        nonce = request.headers.get("X-Lark-Request-Nonce", "")
        signature = request.headers.get("X-Lark-Signature", "")
        if not verify_signature(
            timestamp,
            nonce,
            settings.feishu_encrypt_key,
            raw,
            signature,
        ):
            return JSONResponse({"error": "invalid signature"}, status_code=401)

        header = payload.get("header") if isinstance(payload.get("header"), dict) else {}
        event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
        event_id = str(header.get("event_id") or "").strip()
        event_type = str(header.get("event_type") or "").strip()
        document_id = str(event.get("document_id") or event.get("file_token") or "").strip()
        folder_token = str(event.get("folder_token") or "").strip()

        if not event_id or not document_id:
            return JSONResponse(
                {"error": "missing event_id or document_id"},
                status_code=400,
            )

        logger.info(
            "feishu_event received event_id=%s event_type=%s document_id=%s folder_token_empty=%s",
            event_id,
            event_type,
            document_id,
            not bool(folder_token),
        )

        # drive.file.edit_v1 等无 folder_token：列目录无法在飞书 3s 内稳定完成（含隧道 RTT），改入队由 worker 解析
        if not folder_token:
            if not settings.feishu_app_id.strip() or not settings.feishu_app_secret.strip():
                return JSONResponse(
                    {
                        "error": "folder_token_missing_and_no_feishu_app_credentials",
                    },
                    status_code=400,
                )
            if event_type.startswith("drive.file."):
                ik, rq_doc_type, resource_plane = resolve_drive_file_ingest(
                    event, settings, event_type=event_type
                )
            else:
                try:
                    ik = derive_ingest_kind(event, header)
                except ValueError as exc:
                    return JSONResponse({"error": str(exc)}, status_code=400)
                resource_plane = (
                    "cloud_docx" if ik == "cloud_docx" else "drive_file"
                )
                rq_doc_type = (
                    normalize_drive_doc_type(event, event_type=event_type)
                    if ik == "drive_file"
                    else None
                )
            sub_kw: dict[str, str] = {}
            if event_type == "drive.file.created_in_folder_v1":
                sft = resolve_subscribe_file_type_for_created_in_folder(
                    event, ik, rq_doc_type
                )
                if sft:
                    sub_kw["drive_subscribe_file_type"] = sft
            queue.enqueue(
                "ingest_feishu_document_event",
                event_id=event_id,
                document_id=document_id,
                event_type=event_type,
                folder_token="",
                ingest_kind=ik,
                doc_type=rq_doc_type,
                resource_plane=resource_plane,
                **sub_kw,
            )
            return JSONResponse({"code": 0, "msg": "ok"})

        route = resolve_folder_route(routing_config, folder_token)
        if route is None:
            return JSONResponse({"error": "folder_route_not_resolved"}, status_code=400)
        if event_type.startswith("drive.file."):
            ingest_kind, snap_doc_type, resource_plane = resolve_drive_file_ingest(
                event, settings, event_type=event_type
            )
        else:
            try:
                ingest_kind = derive_ingest_kind(event, header)
            except ValueError as exc:
                return JSONResponse({"error": str(exc)}, status_code=400)
            resource_plane = (
                "cloud_docx" if ingest_kind == "cloud_docx" else "drive_file"
            )
            snap_doc_type = (
                normalize_drive_doc_type(event, event_type=event_type)
                if ingest_kind == "drive_file"
                else None
            )
        maybe_per_doc_subscribe_on_created_in_folder(
            settings=settings,
            event=event,
            event_type=event_type,
            document_id=document_id,
            ingest_kind=ingest_kind,
            doc_type=snap_doc_type,
        )
        if not state_store.try_mark_event_seen(event_id):
            return JSONResponse({"code": 0, "msg": "duplicate"})

        version = state_store.next_version(document_id)
        snapshot = DocumentSnapshot(
            event_id=event_id,
            document_id=document_id,
            folder_token=folder_token,
            event_type=event_type,
            qa_rule_file=route.qa_rule_file,
            dataset_id=route.dataset_id,
            workspace_path=routing_config.pipeline_workspace.path,
            cursor_timeout_seconds=routing_config.pipeline_workspace.cursor_timeout_seconds,
            received_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            version=version,
            dify_target_key=route.dify_target_key,
            ingest_kind=ingest_kind,
            resource_plane=resource_plane,
            doc_type=snap_doc_type,
        )
        state_store.save_snapshot(snapshot)
        queue.enqueue("schedule_document_job", document_id=document_id, version=version)
        return JSONResponse({"code": 0, "msg": "ok"})

    return app


def build_app() -> FastAPI:
    settings = get_executor_settings()
    routing_config = load_routing_config(settings)
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    state_store = RedisStateStore(redis_client=redis_client)
    queue = RQQueueAdapter(
        queue=Queue(settings.vla_queue_name, connection=redis_client)
    )
    return create_app(
        settings=settings,
        routing_config=routing_config,
        state_store=state_store,
        queue=queue,
    )
