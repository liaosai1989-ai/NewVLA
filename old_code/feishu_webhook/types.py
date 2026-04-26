"""Shared Feishu webhook types."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

log = logging.getLogger(__name__)


class FeishuIngestKind(str, Enum):
    CLOUD_DOCX = "cloud_docx"
    DRIVE_FILE = "drive_file"


def coerce_feishu_ingest_kind(value: Any) -> FeishuIngestKind:
    if isinstance(value, FeishuIngestKind):
        return value
    if value is None or value == "":
        return FeishuIngestKind.CLOUD_DOCX
    try:
        return FeishuIngestKind(str(value).strip())
    except ValueError:
        log.warning("invalid feishu_ingest_kind %r, default to cloud_docx", value)
        return FeishuIngestKind.CLOUD_DOCX

