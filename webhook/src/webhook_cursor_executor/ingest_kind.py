from __future__ import annotations

from typing import Any


def derive_ingest_kind(event: dict[str, Any], header: dict[str, Any]) -> str:
    """Map Feishu callback payload to ``feishu_fetch`` ingest kind.

    Convention (single source for app + HTTP enqueue; worker must use RQ arg):

    - ``drive.file.*`` (header or event ``event_type``) → ``drive_file``.
    - Cloud doc / wiki style events → ``cloud_docx`` when ``event_type`` starts
      with ``docx.`` or contains the substring ``wiki`` (case-insensitive), matching
      Feishu doc/wiki subscriber naming in this codebase.
    - Any other ``event_type`` → :class:`ValueError` (caller should map to HTTP 4xx).

    ``event_type`` is read from ``header`` first, then ``event``.
    """
    ev = event if isinstance(event, dict) else {}
    hdr = header if isinstance(header, dict) else {}
    et = str(hdr.get("event_type") or ev.get("event_type") or "").strip()
    if not et:
        raise ValueError("missing event_type for ingest_kind derivation")
    lower = et.lower()
    if et.startswith("drive.file."):
        return "drive_file"
    if et.startswith("docx.") or "wiki" in lower:
        return "cloud_docx"
    raise ValueError(f"unknown event_type for ingest_kind: {et!r}")
