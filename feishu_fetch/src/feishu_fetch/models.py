from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Literal

from .errors import build_error

SupportedIngestKind = Literal["cloud_docx", "drive_file"]
SupportedDocType = Literal["file", "doc", "docx", "sheet"]


@dataclass(frozen=True)
class FeishuFetchRequest:
    ingest_kind: SupportedIngestKind
    output_dir: str | Path
    document_id: str | None = None
    file_token: str | None = None
    doc_type: str | None = None
    title_hint: str | None = None
    timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        output_dir = Path(self.output_dir)
        object.__setattr__(self, "output_dir", output_dir)

        if self.timeout_seconds is not None:
            try:
                timeout_seconds = float(self.timeout_seconds)
            except (TypeError, ValueError) as exc:
                raise build_error(
                    code="request_error",
                    reason="timeout_seconds 不是合法数字",
                    advice="改为大于 0 的有限数字后重试",
                    detail={"timeout_seconds": self.timeout_seconds},
                ) from exc
            if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
                raise build_error(
                    code="request_error",
                    reason="timeout_seconds 必须是大于 0 的有限数字",
                    advice="改为大于 0 的有限数字后重试",
                    detail={"timeout_seconds": self.timeout_seconds},
                )
            object.__setattr__(self, "timeout_seconds", timeout_seconds)

        if self.ingest_kind == "cloud_docx":
            if not (self.document_id or "").strip():
                raise build_error(
                    code="request_error",
                    reason="cloud_docx 请求必须提供 document_id",
                    advice="把 document_id 显式写入 FeishuFetchRequest 后重试",
                    detail={"ingest_kind": self.ingest_kind},
                )
            return

        if self.ingest_kind == "drive_file":
            if (self.document_id or "").strip() and not (self.file_token or "").strip():
                raise build_error(
                    code="request_error",
                    reason="不能把 document_id 当作 drive_file 的兜底输入",
                    advice="改为显式提供 file_token 和 doc_type",
                    detail={
                        "ingest_kind": self.ingest_kind,
                        "document_id": self.document_id,
                    },
                )
            if not (self.file_token or "").strip() or not (self.doc_type or "").strip():
                raise build_error(
                    code="request_error",
                    reason="drive_file 请求必须同时提供 file_token 和 doc_type",
                    advice="补全 file_token 和 doc_type 后重试",
                    detail={"ingest_kind": self.ingest_kind},
                )
            if self.doc_type not in {"file", "doc", "docx", "sheet"}:
                raise build_error(
                    code="request_error",
                    reason="doc_type 不在第一版支持范围内",
                    advice="只使用 file、doc、docx、sheet 四种 doc_type",
                    detail={
                        "ingest_kind": self.ingest_kind,
                        "doc_type": self.doc_type,
                    },
                )
            return

        raise build_error(
            code="request_error",
            reason=f"ingest_kind 不支持：{self.ingest_kind}",
            advice="改为 cloud_docx 或 drive_file",
            detail={"ingest_kind": self.ingest_kind},
        )


@dataclass(frozen=True)
class FeishuFetchResult:
    artifact_path: str
    ingest_kind: SupportedIngestKind
    title: str | None = None
