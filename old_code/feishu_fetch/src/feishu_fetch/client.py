from __future__ import annotations

import time
from typing import Any

import httpx

from .config import FeishuFetchConfig

_token_cache: dict[tuple[str, str, str], dict[str, Any]] = {}


def _api_base(config: FeishuFetchConfig) -> str:
    return config.feishu_api_base.rstrip("/")


def _cache_key(config: FeishuFetchConfig) -> tuple[str, str, str]:
    return (_api_base(config), config.feishu_app_id, config.feishu_app_secret)


def _build_http_client(config: FeishuFetchConfig) -> httpx.Client:
    return httpx.Client(
        timeout=config.request_timeout_seconds,
        verify=config.verify_ssl,
        follow_redirects=True,
    )


def _client_pair(
    config: FeishuFetchConfig,
    http_client: httpx.Client | None,
) -> tuple[httpx.Client, bool]:
    if http_client is not None:
        return http_client, False
    return _build_http_client(config), True


def _feishu_api_json_response(r: httpx.Response) -> dict[str, Any]:
    try:
        data = r.json()
    except Exception:
        return {"code": -1, "msg": f"non_json_http_{r.status_code}"}
    if not isinstance(data, dict):
        return {"code": -1, "msg": "invalid_response_shape"}
    return data


def _parse_token_payload(data: dict[str, Any]) -> tuple[str, int]:
    token = data.get("tenant_access_token")
    expire = data.get("expire")
    if not isinstance(token, str) or not token:
        raise RuntimeError("feishu token malformed response")
    try:
        expire_seconds = int(expire)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("feishu token malformed response") from exc
    if expire_seconds <= 0:
        raise RuntimeError("feishu token malformed response")
    return token, expire_seconds


def get_tenant_access_token(
    config: FeishuFetchConfig,
    *,
    http_client: httpx.Client | None = None,
) -> str:
    now = time.monotonic()
    key = _cache_key(config)
    cached = _token_cache.get(key)
    if cached and cached["token"] and now < float(cached["expire_at"]):
        return str(cached["token"])

    client, should_close = _client_pair(config, http_client)
    try:
        r = client.post(
            f"{_api_base(config)}/open-apis/auth/v3/tenant_access_token/internal",
            json={
                "app_id": config.feishu_app_id,
                "app_secret": config.feishu_app_secret,
            },
        )
    finally:
        if should_close:
            client.close()

    if r.status_code >= 400:
        raise RuntimeError(
            f"feishu token permanent: status={r.status_code} reason={r.reason_phrase}"
        )
    data = _feishu_api_json_response(r)
    if data.get("code") != 0:
        raise RuntimeError(f"feishu token api error: feishu_code={data.get('code')}")
    token, expire = _parse_token_payload(data)
    _token_cache[key] = {"token": token, "expire_at": now + max(60, expire - 120)}
    return token


def get_drive_file_metadata(
    config: FeishuFetchConfig,
    file_token: str,
    *,
    doc_type: str,
    http_client: httpx.Client | None = None,
) -> dict[str, Any]:
    client, should_close = _client_pair(config, http_client)
    try:
        access = get_tenant_access_token(config, http_client=client)
        r = client.post(
            f"{_api_base(config)}/open-apis/drive/v1/metas/batch_query",
            headers={
                "Authorization": f"Bearer {access}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json={"request_docs": [{"doc_token": file_token.strip(), "doc_type": doc_type}]},
        )
    finally:
        if should_close:
            client.close()

    data = _feishu_api_json_response(r)
    if data.get("code") != 0:
        raise RuntimeError(
            f"feishu metas_batch_query permanent: feishu_code={data.get('code', 'n/a')}"
        )
    metas = (data.get("data") or {}).get("metas")
    if not isinstance(metas, list) or not metas:
        raise RuntimeError("feishu metas_batch_query empty metas")
    first = metas[0]
    if not isinstance(first, dict):
        raise RuntimeError("feishu metas_batch_query bad meta")
    return first


def download_drive_file(
    config: FeishuFetchConfig,
    file_token: str,
    *,
    http_client: httpx.Client | None = None,
    max_download_bytes: int = 20 * 1024 * 1024,
) -> bytes:
    client, should_close = _client_pair(config, http_client)
    try:
        access = get_tenant_access_token(config, http_client=client)
        r = client.get(
            f"{_api_base(config)}/open-apis/drive/v1/files/{file_token.strip()}/download",
            headers={"Authorization": f"Bearer {access}"},
        )
    finally:
        if should_close:
            client.close()

    if r.status_code >= 400:
        raise RuntimeError(
            f"feishu drive permanent: status={r.status_code} reason={r.reason_phrase}"
        )
    content_length = r.headers.get("Content-Length")
    if content_length:
        try:
            content_length_value = int(content_length)
        except ValueError as exc:
            raise RuntimeError("download invalid content-length") from exc
        if content_length_value > max_download_bytes:
            raise RuntimeError("download too large")
    body = bytes(r.content or b"")
    if len(body) > max_download_bytes:
        raise RuntimeError("download too large")
    return body


def get_docx_raw_content(
    config: FeishuFetchConfig,
    document_id: str,
    *,
    http_client: httpx.Client | None = None,
) -> str:
    client, should_close = _client_pair(config, http_client)
    try:
        access = get_tenant_access_token(config, http_client=client)
        r = client.get(
            f"{_api_base(config)}/open-apis/docx/v1/documents/{document_id}/raw_content",
            headers={"Authorization": f"Bearer {access}"},
        )
    finally:
        if should_close:
            client.close()

    if r.status_code >= 400:
        raise RuntimeError(
            f"feishu docx permanent: status={r.status_code} reason={r.reason_phrase}"
        )
    data = _feishu_api_json_response(r)
    if data.get("code") != 0:
        raise RuntimeError(f"docx raw_content api error: feishu_code={data.get('code')}")
    inner = data.get("data") or {}
    return str(inner.get("content") or "")
