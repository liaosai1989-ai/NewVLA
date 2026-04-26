from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote, urlparse

from .types import FeishuIngestKind


class FeishuLinkParseError(ValueError):
    pass


_FEISHUISH_HOST_SUFFIXES = (
    "feishu.cn",
    "larksuite.com",
    "larkoffice.com",
)


@dataclass(frozen=True)
class ParsedFeishuLink:
    token: str
    ingest_kind: FeishuIngestKind
    file_type_hint: str | None


def _clean_token(raw: str) -> str:
    s = unquote((raw or "").strip())
    s = s.split("?", 1)[0].split("#", 1)[0].strip().rstrip("/")
    return s


def _path_parts(url: str) -> list[str]:
    p = urlparse(url.strip())
    return [x for x in (p.path or "").split("/") if x]


def _is_feishuish_host(host: str) -> bool:
    h = (host or "").lower().strip(".")
    return any(h == s or h.endswith("." + s) for s in _FEISHUISH_HOST_SUFFIXES)


def _match_exact_path_tuple(parts: list[str], expected: tuple[str, ...]) -> str | None:
    if len(parts) != len(expected) + 1:
        return None
    if [part.lower() for part in parts[:-1]] != [part.lower() for part in expected]:
        return None
    tok = _clean_token(parts[-1])
    return tok or None


def parse_feishu_file_url(url: str) -> ParsedFeishuLink:
    raw = (url or "").strip()
    if not raw:
        raise FeishuLinkParseError("empty url")

    parsed = urlparse(raw)
    if (parsed.scheme or "").lower() != "https":
        raise FeishuLinkParseError("expected absolute https URL")

    host = (parsed.hostname or "").lower()
    if not host:
        raise FeishuLinkParseError("expected absolute https URL with non-empty host")

    if not _is_feishuish_host(host):
        raise FeishuLinkParseError(
            f"unexpected host {host!r}; expected feishu.cn / larksuite.com / larkoffice.com"
        )

    parts = _path_parts(raw)

    if "folder" in [p.lower() for p in parts]:
        raise FeishuLinkParseError(
            "链接指向文件夹。请打开具体文件后复制浏览器地址（需包含文件 token）。"
        )

    allowed_paths: list[tuple[tuple[str, ...], FeishuIngestKind, str | None]] = [
        (("docx",), FeishuIngestKind.CLOUD_DOCX, "docx"),
        (("sheets",), FeishuIngestKind.DRIVE_FILE, "sheet"),
        (("sheet",), FeishuIngestKind.DRIVE_FILE, "sheet"),
        (("base",), FeishuIngestKind.DRIVE_FILE, "bitable"),
        (("bitable",), FeishuIngestKind.DRIVE_FILE, "bitable"),
        (("slides",), FeishuIngestKind.DRIVE_FILE, "slides"),
        (("slide",), FeishuIngestKind.DRIVE_FILE, "slides"),
        (("mindnotes",), FeishuIngestKind.DRIVE_FILE, "mindnote"),
        (("mindnote",), FeishuIngestKind.DRIVE_FILE, "mindnote"),
        (("file",), FeishuIngestKind.DRIVE_FILE, "file"),
        (("drive", "file"), FeishuIngestKind.DRIVE_FILE, "file"),
    ]
    for path_prefix, ingest_kind, file_type_hint in allowed_paths:
        tok = _match_exact_path_tuple(parts, path_prefix)
        if tok:
            return ParsedFeishuLink(tok, ingest_kind, file_type_hint)

    raise FeishuLinkParseError(
        "无法从 URL 识别文件类型与 token。请使用标准浏览器文件链接。"
    )
