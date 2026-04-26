from __future__ import annotations

import io
import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Any

from markitdown import MarkItDown

_MARKITDOWN_EXT = frozenset({".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls"})
_TEXT_EXT = frozenset(
    {
        ".txt",
        ".log",
        ".md",
        ".markdown",
        ".csv",
        ".tsv",
        ".json",
        ".jsonl",
        ".xml",
        ".yaml",
        ".yml",
        ".svg",
    }
)
_HTML_EXT = frozenset({".html", ".htm", ".xhtml"})
_IMAGE_EXT = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".tif", ".tiff"}
)
_DOC_TYPE_EXT: dict[str, str] = {
    "sheet": ".xlsx",
    "bitable": ".xlsx",
    "slides": ".pptx",
    "doc": ".doc",
    "docx": ".docx",
}


class DriveNormalizeError(Exception):
    def __init__(
        self,
        message: str,
        *,
        permanent: bool = True,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.permanent = permanent
        self.detail = detail or {}


def _mime_base(mime: str | None) -> str | None:
    if not mime:
        return None
    return mime.split(";", 1)[0].strip().lower() or None


def _resolve_extension(
    meta: dict[str, Any],
    http_content_type: str | None,
    file_bytes: bytes,
) -> tuple[str, str]:
    title = str(meta.get("title") or "").strip()
    ext = Path(title).suffix.lower() if title else ""
    if not ext:
        ext = _DOC_TYPE_EXT.get(str(meta.get("doc_type") or "").lower(), "")
    mime = _mime_base(http_content_type)
    if not ext and mime == "text/plain":
        ext = ".txt"
    if not ext and mime in ("text/html", "application/xhtml+xml"):
        ext = ".html"
    if not ext and mime == "application/pdf":
        ext = ".pdf"
    if not ext and file_bytes[:4] == b"%PDF":
        ext = ".pdf"
    token = str(meta.get("doc_token") or meta.get("document_id") or "file")
    return ext, f"{token}{ext}" if ext else token


def _decode_text_blob(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    no_script = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    no_style = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", no_script)
    text = re.sub(r"(?s)<[^>]+>", " ", no_style)
    return re.sub(r"\s+", " ", text).strip()


def _markitdown_to_text(
    file_bytes: bytes,
    filename: str,
    *,
    wall_clock_timeout_sec: float,
) -> str:
    def _run() -> str:
        md = MarkItDown(enable_plugins=False)
        result = md.convert_stream(io.BytesIO(file_bytes), filename=filename)
        return str(result.text_content or "").strip()

    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_run)
    timed_out = False
    try:
        return future.result(timeout=wall_clock_timeout_sec)
    except FuturesTimeoutError as exc:
        timed_out = True
        future.cancel()
        raise DriveNormalizeError(
            "convert_timeout",
            permanent=False,
            detail={"converter": "markitdown", "reason": "convert_timeout"},
        ) from exc
    except Exception as exc:
        raise DriveNormalizeError(
            f"convert_failed: {exc}",
            detail={"converter": "markitdown", "reason": "convert_failed"},
        ) from exc
    finally:
        pool.shutdown(wait=not timed_out, cancel_futures=timed_out)


def normalize_drive_download(
    *,
    meta: dict[str, Any],
    file_bytes: bytes,
    http_content_type: str | None = None,
    wall_clock_timeout_sec: float = 1800.0,
) -> tuple[str, dict[str, Any]]:
    started_at = time.monotonic()
    mime = _mime_base(http_content_type)
    if mime and mime.startswith("image/"):
        raise DriveNormalizeError("image files are not normalized")

    ext, filename = _resolve_extension(meta, http_content_type, file_bytes)
    if ext in _IMAGE_EXT:
        raise DriveNormalizeError("image files are not normalized")

    detail: dict[str, Any] = {
        "ext": ext or "",
        "synthetic_filename": filename,
        "mime": mime or "",
    }

    if not ext or ext in _TEXT_EXT:
        text = _decode_text_blob(file_bytes)
        detail["converter"] = "direct"
        detail["duration_ms"] = int((time.monotonic() - started_at) * 1000)
        return text, detail

    if ext in _HTML_EXT:
        text = _strip_html(_decode_text_blob(file_bytes))
        detail["converter"] = "html_strip"
        detail["duration_ms"] = int((time.monotonic() - started_at) * 1000)
        return text, detail

    if ext in _MARKITDOWN_EXT:
        text = _markitdown_to_text(
            file_bytes,
            filename,
            wall_clock_timeout_sec=wall_clock_timeout_sec,
        )
        detail["converter"] = "markitdown"
        detail["duration_ms"] = int((time.monotonic() - started_at) * 1000)
        return text, detail

    raise DriveNormalizeError(
        f"unsupported extension: {ext}",
        detail={**detail, "reason": "unsupported_ext"},
    )
