"""飞书 drive「订阅云文档事件」：夹级 subscribe 不足以覆盖编辑推送时，在 `created_in_folder` 后对单文件补订。

见 https://open.feishu.cn/document/server-docs/docs/drive-v1/event/subscribe
非 folder 的 ``file_type`` 仅传 query ``file_type``，不传 ``event_type``。
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from webhook_cursor_executor.feishu_folder_resolve import _get_tenant_access_token
from webhook_cursor_executor.settings import ExecutorSettings

logger = logging.getLogger(__name__)

CREATED_IN_FOLDER_V1 = "drive.file.created_in_folder_v1"

# 与开放平台 subscribe 接口 ``file_type`` 可选值对齐（不含 folder）
DRIVE_SUBSCRIBE_FILE_TYPES = frozenset(
    {"doc", "docx", "sheet", "bitable", "file", "slides"}
)

_HTTP_TIMEOUT = 8.0


def resolve_subscribe_file_type_for_created_in_folder(
    event: dict[str, Any],
    ingest_kind: str,
    doc_type: str | None,
) -> str | None:
    """从 ``drive.file.created_in_folder_v1`` 事件体 + ingest 推断可传给 subscribe API 的 ``file_type``。"""
    ev = event if isinstance(event, dict) else {}
    raw = str(ev.get("file_type") or ev.get("file_type_v2") or "").strip().lower()
    if raw in DRIVE_SUBSCRIBE_FILE_TYPES:
        return raw
    if ingest_kind == "cloud_docx":
        return "docx"
    dt = str(doc_type or "").strip().lower()
    if dt in DRIVE_SUBSCRIBE_FILE_TYPES:
        return dt
    return None


def subscribe_file_type_fallback(ingest_kind: str, doc_type: str | None) -> str | None:
    """worker 无完整 event 时，仅由 ingest_kind / doc_type 回退。"""
    if ingest_kind == "cloud_docx":
        return "docx"
    dt = str(doc_type or "").strip().lower()
    if dt in DRIVE_SUBSCRIBE_FILE_TYPES:
        return dt
    return None


def _post_subscribe_drive_file(
    tenant_token: str,
    file_token: str,
    file_type: str,
) -> tuple[bool, str]:
    q = urlencode({"file_type": file_type})
    path_tok = quote(file_token, safe="")
    url = f"https://open.feishu.cn/open-apis/drive/v1/files/{path_tok}/subscribe?{q}"
    req = Request(
        url,
        headers={"Authorization": f"Bearer {tenant_token}"},
        method="POST",
        data=b"",
    )
    try:
        with urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return False, f"HTTP {exc.code} non-json"
        if isinstance(body, dict):
            c, m = body.get("code"), body.get("msg") or body.get("message")
            return False, f"HTTP {exc.code} code={c} msg={m!s}"[:500]
        return False, f"HTTP {exc.code}"
    except (URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        return False, f"{type(exc).__name__}: {exc!s}"[:500]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False, "subscribe response not json"
    if not isinstance(data, dict):
        return False, "subscribe response not object"
    c = data.get("code")
    if c == 0 or c == "0":
        return True, ""
    m = str(data.get("msg") or data.get("message") or "")
    return False, f"code={c} msg={m}"[:500]


def event_driven_per_doc_subscribe(
    settings: ExecutorSettings,
    file_token: str,
    file_type: str,
) -> None:
    """tenant 对单文件 subscribe；失败只打日志，不中断 ingest。"""
    ft = (file_type or "").strip().lower()
    tok = (file_token or "").strip()
    if not tok or ft not in DRIVE_SUBSCRIBE_FILE_TYPES:
        return
    tenant = _get_tenant_access_token(settings)
    if not tenant:
        logger.warning(
            "per_doc_subscribe_skip_no_tenant file_suffix=%s",
            tok[-8:],
        )
        return
    ok, msg = _post_subscribe_drive_file(tenant, tok, ft)
    if ok:
        logger.info(
            "per_doc_subscribe_ok file_suffix=%s file_type=%s",
            tok[-8:],
            ft,
        )
    else:
        logger.error(
            "per_doc_subscribe_failed file_suffix=%s file_type=%s %s",
            tok[-8:],
            ft,
            msg,
        )


def maybe_per_doc_subscribe_on_created_in_folder(
    *,
    settings: ExecutorSettings,
    event: dict[str, Any],
    event_type: str,
    document_id: str,
    ingest_kind: str,
    doc_type: str | None,
) -> None:
    if event_type != CREATED_IN_FOLDER_V1:
        return
    sub_ft = resolve_subscribe_file_type_for_created_in_folder(
        event, ingest_kind, doc_type
    )
    if not sub_ft:
        logger.info(
            "per_doc_subscribe_skip_unmapped event_file_type=%r document_suffix=%s",
            event.get("file_type") if isinstance(event, dict) else None,
            document_id[-8:] if document_id else "",
        )
        return
    event_driven_per_doc_subscribe(settings, document_id, sub_ft)
