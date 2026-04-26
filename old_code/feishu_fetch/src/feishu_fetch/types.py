from __future__ import annotations

from enum import Enum
from typing import Any


class FeishuIngestKind(str, Enum):
    CLOUD_DOCX = "cloud_docx"
    DRIVE_FILE = "drive_file"


def feishu_meta_doc_type_for_hint(file_type_hint: str | None) -> str:
    h = (file_type_hint or "").strip().lower()
    allowed = {
        "file": "file",
        "doc": "doc",
        "docx": "docx",
        "sheet": "sheet",
        "bitable": "bitable",
        "slides": "slides",
        "mindnote": "mindnote",
    }
    if h in allowed:
        return allowed[h]
    raise ValueError(f"unsupported file_type_hint: {file_type_hint!r}")


def coerce_feishu_ingest_kind(value: Any) -> FeishuIngestKind:
    if isinstance(value, FeishuIngestKind):
        return value
    s = str(value).strip()
    try:
        return FeishuIngestKind(s)
    except ValueError as e:
        raise ValueError(f"invalid feishu_ingest_kind: {value!r}") from e
