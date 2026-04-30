"""
drive.file.* 回调里 ``file_token`` 可能是：
  - 新版云文档 ``document_id``（浏览器 ``/docx/{document_id}``）→ ``ingest_kind=cloud_docx``；
  - 云空间 ``file_token``（浏览器 ``/file/{file_token}``）→ ``ingest_kind=drive_file``。

用法：GET ``/open-apis/docx/v1/documents/:document_id``（[获取文档基本信息](https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/document-docx/docx-v1/document/get)）；
code=0 视为云文档；典型不存在为 404 / 业务 not found。

无租户凭证或网络失败时回退事件体 ``file_type``（docx/doc → 云文档，否则 drive），避免纯猜 URL。
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from webhook_cursor_executor.drive_doc_type import normalize_drive_doc_type
from webhook_cursor_executor.feishu_folder_resolve import _get_tenant_access_token
from webhook_cursor_executor.settings import ExecutorSettings

logger = logging.getLogger(__name__)

_DOCX_DOCUMENT_GET_BASE = "https://open.feishu.cn/open-apis/docx/v1/documents"
_HTTP_TIMEOUT = 1.6


def _feishu_body_ok(body: dict[str, Any]) -> bool:
    c = body.get("code")
    return c == 0 or c == "0"


def probe_docx_document_readable(settings: ExecutorSettings, token: str) -> bool | None:
    """``True``=docx API 可读；``False``=明确不是云文档 docx；``None``=未探测（无凭证/网络错误/非明确否）。"""
    tid = (token or "").strip()
    if not tid:
        return None
    tenant = _get_tenant_access_token(settings)
    if not tenant:
        return None
    url = f"{_DOCX_DOCUMENT_GET_BASE}/{tid}"
    req = Request(
        url,
        headers={"Authorization": f"Bearer {tenant}"},
        method="GET",
    )
    try:
        with urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("docx_probe_http_error status=%s url_suffix=…%s", exc.code, tid[-8:])
            return None
        code = body.get("code")
        # 文档不存在 / 已删
        if code in (1770002, "1770002"):
            return False
        if exc.code == 404:
            return False
        logger.info("docx_probe_negative code=%s http=%s token_suffix=%s", code, exc.code, tid[-8:])
        return None
    except (URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("docx_probe_network_error %s token_suffix=%s", type(exc).__name__, tid[-8:])
        return None

    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if _feishu_body_ok(body) and isinstance(body.get("data"), dict):
        return True
    code = body.get("code")
    if code in (1770002, "1770002"):
        return False
    return None


def _event_hints_cloud_docx(event: dict[str, Any]) -> bool:
    raw = str(event.get("file_type") or event.get("file_type_v2") or "").strip().lower()
    # 飞书 drive 事件里 doc/docx 多指云文档类型；file 指上传文件 → drive 链
    return raw in frozenset({"docx", "doc"})


def resolve_drive_file_ingest(
    event: dict[str, Any],
    settings: ExecutorSettings,
    *,
    event_type: str = "",
) -> tuple[str, str | None, str]:
    """返回 ``(ingest_kind, doc_type, resource_plane)``。"""
    ev = event if isinstance(event, dict) else {}
    token = str(ev.get("document_id") or ev.get("file_token") or "").strip()
    probe = probe_docx_document_readable(settings, token)
    if probe is True:
        return "cloud_docx", None, "cloud_docx"
    if probe is False:
        return (
            "drive_file",
            normalize_drive_doc_type(ev, event_type=event_type),
            "drive_file",
        )
    if _event_hints_cloud_docx(ev):
        return "cloud_docx", None, "cloud_docx"
    return (
        "drive_file",
        normalize_drive_doc_type(ev, event_type=event_type),
        "drive_file",
    )
