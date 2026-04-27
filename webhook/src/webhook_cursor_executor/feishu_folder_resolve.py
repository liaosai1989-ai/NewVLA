"""
drive.file.edit_v1 等事件的 event 体不含 folder_token（见飞书 open 文档「文件编辑」）；
在具备 FEISHU_APP_ID / FEISHU_APP_SECRET 时，用 tenant token + 列举文件夹下文件
判断 file_token 是否落在已配置的某个 folder_token 下，以恢复路由 key。
只匹配直接子级；子文件夹内文件需另议。
列表项 type=shortcut 时，事件里的 file_token 多为目标文档 token，需同时匹配 shortcut_info.target_token。
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from webhook_cursor_executor.settings import ExecutorSettings, FolderRoute, RoutingConfig

TENANT_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
FILES_LIST_BASE = "https://open.feishu.cn/open-apis/drive/v1/files"

# 飞书事件回调全链路常限 3s；单次 HTTP 不宜过长。鉴权有缓存，列目录可并行
_HTTP_TIMEOUT_LIST = 1.6
_HTTP_TIMEOUT_AUTH = 1.8

_tenant_lock = threading.Lock()
# app_id -> (token, expire_at_unix wall time)
_tenant_memo: dict[str, tuple[str, float]] = {}


def _feishu_api_ok(body: dict[str, Any]) -> bool:
    # 注意：code==0 时不可写 (body.get("code") or -1) — 会把 0 当成假值变成 -1
    c = body.get("code")
    return c == 0 or c == "0"


def _get_tenant_access_token(settings: ExecutorSettings) -> str | None:
    app_id = settings.feishu_app_id.strip()
    secret = settings.feishu_app_secret.strip()
    if not app_id or not secret:
        return None
    now = time.time()
    with _tenant_lock:
        if app_id in _tenant_memo:
            tok, exp = _tenant_memo[app_id]
            if now < exp:
                return tok
    body = json.dumps({"app_id": app_id, "app_secret": secret}).encode("utf-8")
    req = Request(
        TENANT_TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=_HTTP_TIMEOUT_AUTH) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not _feishu_api_ok(data):
        return None
    token = (data.get("tenant_access_token") or data.get("app_access_token") or "").strip()
    if not token:
        return None
    try:
        ttl = int(data.get("expire") or 7200)
    except (TypeError, ValueError):
        ttl = 7200
    # 提前 5 分钟刷新，避免边界上 401
    until = now + max(120, ttl - 300)
    with _tenant_lock:
        _tenant_memo[app_id] = (token, until)
    return token


def _folder_list_page(
    tenant_token: str,
    folder_token: str,
    page_token: str | None,
) -> dict[str, Any] | None:
    q: dict[str, Any] = {
        "folder_token": folder_token,
        "page_size": 200,
    }
    if page_token:
        q["page_token"] = page_token
    url = f"{FILES_LIST_BASE}?{urlencode(q)}"
    req = Request(
        url,
        headers={"Authorization": f"Bearer {tenant_token}"},
        method="GET",
    )
    try:
        with urlopen(req, timeout=_HTTP_TIMEOUT_LIST) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError):
        return None


def _file_entry_matches_target(file_obj: dict[str, Any], target: str) -> bool:
    """单行 files[]：实体 token 或快捷方式指向的 target_token（与飞书列目录文档一致）。"""
    if not target:
        return False
    t = file_obj.get("token")
    if isinstance(t, str) and t == target:
        return True
    info = file_obj.get("shortcut_info")
    if isinstance(info, dict):
        tt = info.get("target_token")
        if isinstance(tt, str) and tt == target:
            return True
    return False


def _file_token_in_list(payload: dict[str, Any], target: str) -> bool:
    if not target:
        return False
    data = payload.get("data") or {}
    files = data.get("files")
    if not isinstance(files, list):
        return False
    for f in files:
        if not isinstance(f, dict):
            continue
        if _file_entry_matches_target(f, target):
            return True
    return False


def _folder_contains_with_tenant(
    tenant: str,
    folder_token: str,
    file_token: str,
) -> bool:
    page_token: str | None = None
    for _ in range(50):
        raw = _folder_list_page(tenant, folder_token, page_token)
        if raw is None or not _feishu_api_ok(raw):
            return False
        if _file_token_in_list(raw, file_token):
            return True
        data = raw.get("data")
        if not isinstance(data, dict):
            return False
        nxt = data.get("page_token")
        if isinstance(nxt, str) and nxt.strip():
            page_token = nxt
            continue
        return False
    return False


def resolve_folder_token_by_listing(
    *,
    routing_config: RoutingConfig,
    file_token: str,
    settings: ExecutorSettings,
) -> str | None:
    if not file_token:
        return None
    if not settings.feishu_app_id.strip() or not settings.feishu_app_secret.strip():
        return None
    routes = routing_config.folder_routes
    if not routes:
        return None
    tenant = _get_tenant_access_token(settings)
    if not tenant:
        return None
    # 多夹须与单夹语义一致：逐夹列目录直到命中。勿用 as_completed(..., timeout)：
    # 错误夹若先快速返回 False，等正确夹时下一轮 __next__ 仍受同一 timeout，易 TimeoutError → 误判无路由。
    # 列目录在 worker ingest 内执行，不受飞书 webhook 3s 限制。
    for route in routes:
        try:
            if _folder_contains_with_tenant(tenant, route.folder_token, file_token):
                return route.folder_token
        except (OSError, ValueError, RuntimeError):
            continue
    return None


def resolve_folder_route(
    routing_config: RoutingConfig,
    folder_token: str,
) -> FolderRoute | None:
    if not folder_token.strip():
        return None
    for route in routing_config.folder_routes:
        if route.folder_token == folder_token:
            return route
    return None
