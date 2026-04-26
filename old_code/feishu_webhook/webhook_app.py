from __future__ import annotations

import json
import logging
import re
from contextlib import asynccontextmanager
from typing import Any, Protocol

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from redis import Redis

from feishu_webhook.crypto import parse_request_body, verify_signature
from feishu_webhook.events import extract_event_folder_token, extract_feishu_ingest
from feishu_webhook.queue_rq import (
    RQQueueAdapter,
    build_rq_queue_from_settings,
    build_rq_redis,
    build_state_redis,
)
from feishu_webhook.settings import WebhookSettings, get_webhook_settings
from feishu_webhook.types import FeishuIngestKind
from feishu_webhook.webhook_debounce import schedule_feishu_doc_enqueue_after_webhook

log = logging.getLogger(__name__)

_JSON_UTF8 = "application/json; charset=utf-8"


class FeishuWebhookClient(Protocol):
    def subscribe_drive_file_events(
        self,
        file_token: str,
        *,
        file_type: str = "docx",
    ) -> dict[str, Any]:
        ...

    def subscribe_folder_file_created(self, folder_token: str) -> dict[str, Any]:
        ...


def _challenge_response(payload: dict[str, Any]) -> dict[str, str] | None:
    if payload.get("type") == "url_verification" and "challenge" in payload:
        return {"challenge": str(payload["challenge"])}

    header = payload.get("header") or {}
    if str(header.get("event_type", "")).lower() == "url_verification":
        event = payload.get("event") or {}
        if "challenge" in event:
            return {"challenge": str(event["challenge"])}
        if "challenge" in payload:
            return {"challenge": str(payload["challenge"])}
    return None


def _verification_token_ok(inner: dict[str, Any], settings: WebhookSettings) -> bool:
    expected = (settings.feishu_verification_token or "").strip()
    if not expected:
        return True

    header = inner.get("header") or {}
    token = header.get("token") if isinstance(header.get("token"), str) else None
    if token is None and isinstance(inner.get("token"), str):
        token = inner.get("token")
    return isinstance(token, str) and token == expected


def _try_encrypted_url_verification_challenge(
    settings: WebhookSettings,
    raw: bytes,
) -> dict[str, str] | JSONResponse | None:
    if not settings.feishu_encrypt_key or not raw:
        return None

    try:
        outer = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(outer, dict) or "encrypt" not in outer:
        return None

    try:
        inner = parse_request_body(settings.feishu_encrypt_key, raw)
    except Exception:
        return None

    challenge = _challenge_response(inner)
    if not challenge:
        return None

    if not _verification_token_ok(inner, settings):
        return JSONResponse(
            {"error": "invalid verification token"},
            status_code=403,
            media_type=_JSON_UTF8,
        )

    return challenge


def _parse_body(settings: WebhookSettings, raw: bytes) -> dict[str, Any]:
    if settings.feishu_encrypt_key:
        return parse_request_body(settings.feishu_encrypt_key, raw)
    return json.loads(raw.decode("utf-8"))


def _iter_presubscribe_docx_tokens(raw: str) -> list[str]:
    parts = re.split(r"[\s,]+", (raw or "").strip())
    return [part.strip() for part in parts if part.strip()]


def _ensure_docx_subscribed_for_edit(
    *,
    feishu_client: FeishuWebhookClient,
    settings: WebhookSettings,
    state_redis: Redis,
    doc_id: str,
) -> None:
    if not settings.feishu_auto_subscribe_docx:
        return
    if not settings.feishu_app_id or not settings.feishu_app_secret:
        return

    key = f"webhook:feishu:docx_subscribed:{doc_id}"
    try:
        if not state_redis.set(
            key,
            "1",
            nx=True,
            ex=int(settings.feishu_subscribe_state_ttl_seconds),
        ):
            return
    except Exception:
        log.exception("failed to set docx subscribe gate")
        return

    try:
        data = feishu_client.subscribe_drive_file_events(doc_id, file_type="docx")
        if data.get("code") != 0:
            state_redis.delete(key)
            log.warning("docx subscribe failed: %s", data)
    except Exception:
        try:
            state_redis.delete(key)
        except Exception:
            log.exception("failed to clear docx subscribe gate after error")
        raise


def _presubscribe_docx_tokens_at_startup(
    *,
    feishu_client: FeishuWebhookClient,
    settings: WebhookSettings,
) -> None:
    tokens = _iter_presubscribe_docx_tokens(settings.feishu_presubscribe_docx_tokens)
    if not tokens:
        return
    if not settings.feishu_app_id or not settings.feishu_app_secret:
        log.warning("skip presubscribe: missing app id/app secret")
        return

    for token in tokens:
        try:
            data = feishu_client.subscribe_drive_file_events(token, file_type="docx")
            if data.get("code") != 0:
                log.warning("presubscribe docx failed token=%s data=%s", token[:12], data)
        except Exception:
            log.exception("presubscribe docx error token=%s", token[:12])


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings: WebhookSettings = app.state.settings
    feishu_client: FeishuWebhookClient = app.state.feishu_client

    folder = (settings.feishu_subscribe_folder_token or "").strip()
    if folder and settings.feishu_app_id and settings.feishu_app_secret:
        try:
            data = feishu_client.subscribe_folder_file_created(folder)
            if data.get("code") != 0:
                log.warning("folder subscribe failed: %s", data)
        except Exception:
            log.exception("folder subscribe failed")

    _presubscribe_docx_tokens_at_startup(
        feishu_client=feishu_client,
        settings=settings,
    )
    yield


def create_app(
    *,
    feishu_client: FeishuWebhookClient,
    settings: WebhookSettings | None = None,
    state_redis: Redis | None = None,
    rq_redis: Redis | None = None,
    queue: RQQueueAdapter | None = None,
) -> FastAPI:
    resolved = settings or get_webhook_settings()

    state_redis = state_redis or build_state_redis(resolved)
    rq_redis = rq_redis or build_rq_redis(resolved)
    queue = queue or build_rq_queue_from_settings(resolved, rq_redis)

    app = FastAPI(title="Feishu Webhook", version="0.1.0", lifespan=_lifespan)
    app.state.settings = resolved
    app.state.state_redis = state_redis
    app.state.rq_redis = rq_redis
    app.state.queue = queue
    app.state.feishu_client = feishu_client

    @app.get("/health")
    def health() -> dict[str, Any]:
        try:
            app.state.state_redis.ping()
            return {"status": "ok", "redis": True}
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={"status": "degraded", "redis": False, "error": str(exc)},
            ) from exc

    @app.post(resolved.feishu_webhook_path)
    async def feishu_webhook(request: Request) -> JSONResponse:
        settings = request.app.state.settings
        state_redis = request.app.state.state_redis
        queue = request.app.state.queue
        feishu_client = request.app.state.feishu_client
        raw = await request.body()

        encrypted_challenge = _try_encrypted_url_verification_challenge(settings, raw)
        if isinstance(encrypted_challenge, JSONResponse):
            return encrypted_challenge
        if isinstance(encrypted_challenge, dict):
            return JSONResponse(encrypted_challenge, media_type=_JSON_UTF8)

        try:
            plain_peek = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            plain_peek = None

        if isinstance(plain_peek, dict) and "encrypt" not in plain_peek:
            plain_challenge = _challenge_response(plain_peek)
            if plain_challenge:
                if not _verification_token_ok(plain_peek, settings):
                    return JSONResponse(
                        {"error": "invalid verification token"},
                        status_code=403,
                        media_type=_JSON_UTF8,
                    )
                return JSONResponse(plain_challenge, media_type=_JSON_UTF8)

        ts = request.headers.get("X-Lark-Request-Timestamp", "")
        nonce = request.headers.get("X-Lark-Request-Nonce", "")
        sig = request.headers.get("X-Lark-Signature", "")
        if not verify_signature(ts, nonce, settings.feishu_encrypt_key, raw, sig):
            return JSONResponse(
                {"error": "invalid signature"},
                status_code=401,
                media_type=_JSON_UTF8,
            )

        try:
            body = _parse_body(settings, raw)
        except Exception:
            log.exception("failed to parse webhook body")
            return JSONResponse(
                {"error": "bad body"},
                status_code=400,
                media_type=_JSON_UTF8,
            )

        challenge = _challenge_response(body)
        if challenge:
            return JSONResponse(challenge, media_type=_JSON_UTF8)

        header = body.get("header") or {}
        event_id = str(header.get("event_id") or body.get("event_id") or "").strip()
        event_type = str(header.get("event_type") or "")

        doc_id, ingest_kind, reason, file_type_hint = extract_feishu_ingest(body)
        if not doc_id or ingest_kind is None:
            log.info("skip webhook: %s", reason)
            return JSONResponse({"code": 0, "msg": "ok"}, media_type=_JSON_UTF8)

        if not event_id:
            return JSONResponse(
                {"error": "missing event_id"},
                status_code=400,
                media_type=_JSON_UTF8,
            )

        dedup_key = f"webhook:event:{event_id}:{doc_id}"
        if not state_redis.set(
            dedup_key,
            "1",
            nx=True,
            ex=int(settings.feishu_event_dedup_ttl_seconds),
        ):
            return JSONResponse({"code": 0, "msg": "duplicate"}, media_type=_JSON_UTF8)

        try:
            if ingest_kind == FeishuIngestKind.CLOUD_DOCX:
                _ensure_docx_subscribed_for_edit(
                    feishu_client=feishu_client,
                    settings=settings,
                    state_redis=state_redis,
                    doc_id=doc_id,
                )

            folder_token = extract_event_folder_token(body) or ""
            debounce_seconds = int(settings.feishu_webhook_doc_debounce_seconds)

            if debounce_seconds <= 0:
                queue.enqueue_document_job(
                    doc_id,
                    event_id,
                    folder_token,
                    feishu_ingest_kind=ingest_kind,
                    feishu_file_type_hint=file_type_hint,
                )
            else:
                schedule_feishu_doc_enqueue_after_webhook(
                    queue=queue,
                    redis_conn=state_redis,
                    doc_id=doc_id,
                    event_id=event_id,
                    folder_token=folder_token,
                    event_type=event_type or "unknown",
                    ingest_kind=ingest_kind,
                    debounce_seconds=debounce_seconds,
                    feishu_file_type_hint=file_type_hint,
                )
        except Exception:
            try:
                state_redis.delete(dedup_key)
            except Exception:
                log.exception("failed to release dedup key after enqueue error")
            raise

        return JSONResponse({"code": 0, "msg": "ok"}, media_type=_JSON_UTF8)

    return app

