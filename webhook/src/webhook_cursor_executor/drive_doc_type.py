"""飞书 drive 事件 ``file_type`` → ``feishu_fetch.FeishuFetchRequest.doc_type``。"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

FETCH_DOC_TYPES = frozenset({"file", "doc", "docx", "sheet"})


def normalize_drive_doc_type(event: dict[str, Any], *, event_type: str = "") -> str:
    """返回 ``FeishuFetchRequest`` 允许的 doc_type；未知或缺失时默认 ``docx``（云文档最常见）。"""
    raw = str(event.get("file_type") or event.get("file_type_v2") or "").strip().lower()
    if raw in FETCH_DOC_TYPES:
        return raw
    if raw:
        logger.warning(
            "drive_doc_type_unmapped file_type=%r event_type=%s defaulting_to_docx",
            raw,
            event_type,
        )
    else:
        logger.info(
            "drive_doc_type_missing event_type=%s defaulting_to_docx",
            event_type,
        )
    return "docx"


def coerce_stored_drive_doc_type(stored: str | None, *, event_type: str = "") -> str:
    """快照里已有 doc_type 时校验；否则默认 docx（与 normalize_drive_doc_type 对齐）。"""
    raw = str(stored or "").strip().lower()
    if raw in FETCH_DOC_TYPES:
        return raw
    if raw:
        logger.warning(
            "snapshot_doc_type_invalid stored=%r event_type=%s defaulting_to_docx",
            stored,
            event_type,
        )
    return "docx"
