"""Parse Feishu event payloads into enqueue inputs."""

from __future__ import annotations

import re
from typing import Any

from feishu_webhook.types import FeishuIngestKind

_DOC_ID_RE = re.compile(r"^[a-zA-Z0-9]{22,27}$")
_DRIVE_FILE_TYPE_HINTS = frozenset(
    {"sheet", "bitable", "doc", "slides", "pdf", "pptx", "ppt"}
)


def _is_docx_context(data: dict[str, Any]) -> bool:
    file_type = str(data.get("file_type") or data.get("file_type_v2") or "").lower()
    if file_type == "docx":
        return True
    object_kind = str(data.get("object_kind") or data.get("obj_type") or "").lower()
    if "docx" in object_kind:
        return True
    event_type = str(data.get("type") or "").lower()
    return "docx" in event_type


def _token_candidates(obj: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for key in ("document_id", "file_token", "token", "obj_token", "file_id"):
        value = obj.get(key)
        if isinstance(value, str) and _DOC_ID_RE.match(value):
            out.append(value)
    return out


def _collect_tokens(event: dict[str, Any]) -> list[str]:
    seen: dict[str, None] = {}
    for token in _token_candidates(event):
        seen.setdefault(token, None)
    file_obj = event.get("file")
    if isinstance(file_obj, dict):
        for token in _token_candidates(file_obj):
            seen.setdefault(token, None)
    return list(seen.keys())


def walk_for_docx_token(obj: Any, depth: int = 0) -> str | None:
    if depth > 8:
        return None
    if isinstance(obj, dict):
        if _is_docx_context(obj):
            for token in _token_candidates(obj):
                return token
        for value in obj.values():
            found = walk_for_docx_token(value, depth + 1)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = walk_for_docx_token(item, depth + 1)
            if found:
                return found
    return None


def extract_event_folder_token(payload: dict[str, Any]) -> str | None:
    if payload.get("type") == "url_verification":
        return None
    event = payload.get("event")
    if not isinstance(event, dict):
        event = payload if isinstance(payload, dict) else {}
    folder_token = event.get("folder_token")
    if isinstance(folder_token, str) and folder_token.strip():
        return folder_token.strip()
    file_obj = event.get("file")
    if isinstance(file_obj, dict):
        nested = file_obj.get("folder_token")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
    return None


def _event_file_type_hint(event: dict[str, Any]) -> str | None:
    value = str(event.get("file_type") or event.get("file_type_v2") or "").strip().lower()
    return value if value else None


def extract_feishu_ingest(
    payload: dict[str, Any],
) -> tuple[str | None, FeishuIngestKind | None, str | None, str | None]:
    if payload.get("type") == "url_verification":
        return None, None, "url_verification", None

    header = payload.get("header") or {}
    event = payload.get("event")
    if not isinstance(event, dict):
        event = payload if payload.get("event") is None else {}

    file_type_hint = _event_file_type_hint(event)
    event_type = str(header.get("event_type") or event.get("type") or "")
    event_type_lower = event_type.lower()
    file_type = str(event.get("file_type") or event.get("file_type_v2") or "").lower()

    if file_type == "file" and "created_in_folder" in event_type_lower:
        token = event.get("file_token") or event.get("document_id")
        if isinstance(token, str) and _DOC_ID_RE.match(token.strip()):
            return token.strip(), FeishuIngestKind.DRIVE_FILE, None, file_type_hint

    if file_type in _DRIVE_FILE_TYPE_HINTS:
        for token in _collect_tokens(event):
            return token, FeishuIngestKind.DRIVE_FILE, None, file_type_hint
        found = walk_for_docx_token(event)
        if found:
            return found, FeishuIngestKind.DRIVE_FILE, None, file_type_hint
        return None, None, f"skip_file_type:{file_type}_no_token", file_type_hint

    if file_type == "file" and "edit" in event_type_lower:
        for token in _collect_tokens(event):
            return token, FeishuIngestKind.DRIVE_FILE, None, file_type_hint

    if file_type and file_type not in ("docx", ""):
        if not walk_for_docx_token(event):
            return None, None, f"skip_file_type:{file_type}", file_type_hint

    if file_type == "docx":
        for token in _token_candidates(event):
            return token, FeishuIngestKind.CLOUD_DOCX, None, file_type_hint
        for token in _collect_tokens(event):
            return token, FeishuIngestKind.CLOUD_DOCX, None, file_type_hint

    token = event.get("file_token") or event.get("document_id")
    if isinstance(token, str) and _DOC_ID_RE.match(token):
        if file_type == "docx" or _is_docx_context(event) or "docx" in event_type_lower:
            return token, FeishuIngestKind.CLOUD_DOCX, None, file_type_hint

    found = walk_for_docx_token(event)
    if found:
        return found, FeishuIngestKind.CLOUD_DOCX, None, file_type_hint

    if event_type or event:
        return None, None, "no_docx_token_in_event", file_type_hint
    return None, None, "empty_event", None

