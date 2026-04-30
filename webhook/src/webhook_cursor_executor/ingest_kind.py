from __future__ import annotations

from typing import Any


def derive_ingest_kind(event: dict[str, Any], header: dict[str, Any]) -> str:
    """Map Feishu callback ``event_type`` to ``feishu_fetch`` ingest kind **仅**非 ``drive.file.*``。

    ``drive.file.*`` 须走 ``resolve_drive_file_ingest()``（OpenAPI 探测 ``document_id`` 是否为云文档）。

    - ``docx.*`` / event_type 含 ``wiki`` → ``cloud_docx``
    - 其它 → :class:`ValueError`
    """
    ev = event if isinstance(event, dict) else {}
    hdr = header if isinstance(header, dict) else {}
    et = str(hdr.get("event_type") or ev.get("event_type") or "").strip()
    if not et:
        raise ValueError("missing event_type for ingest_kind derivation")
    if et.startswith("drive.file."):
        raise ValueError(
            "drive.file.* must use resolve_drive_file_ingest(), not derive_ingest_kind()"
        )
    lower = et.lower()
    if et.startswith("docx.") or "wiki" in lower:
        return "cloud_docx"
    raise ValueError(f"unknown event_type for ingest_kind: {et!r}")
