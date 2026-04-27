from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import DifyTargetConfig


class DifyUploadError(RuntimeError):
    """Base error for dify upload failures."""


class DifyConfigError(DifyUploadError):
    """Raised when the resolved target config is invalid."""


class DifyRequestError(DifyUploadError):
    """Raised when local file checks or the HTTP request fail."""


class DifyResponseError(DifyUploadError):
    """Raised when the Dify response shape or business result is invalid."""


@dataclass(frozen=True)
class UploadResult:
    dataset_id: str
    document_id: str
    batch: str
    response_body: dict[str, Any]


def _read_csv_bytes(csv_path: Path) -> bytes:
    if not csv_path.exists():
        raise DifyRequestError(
            f"dify request error: file does not exist: {csv_path}"
        )
    if csv_path.suffix.lower() != ".csv":
        raise DifyRequestError(
            "dify request error: file is not csv; only .csv is supported in v1"
        )
    try:
        return csv_path.read_bytes()
    except OSError as exc:
        raise DifyRequestError(
            f"dify request error: file is not readable: {csv_path}"
        ) from exc


def _pick_document_id(node: Any) -> str | None:
    if not isinstance(node, dict):
        return None
    raw = node.get("id")
    text = "" if raw is None else str(raw).strip()
    return text or None


def _extract_document_id(body: dict[str, Any]) -> str:
    primary = _pick_document_id(body.get("document"))
    if primary:
        return primary

    data_node = body.get("data")
    if isinstance(data_node, dict):
        fallback = _pick_document_id(data_node.get("document"))
        if fallback:
            return fallback

    raise DifyResponseError("dify response error: missing document_id in response body")


def _parse_json_body(response: Any) -> dict[str, Any]:
    try:
        body = response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise DifyResponseError(
            "dify response error: response is not valid JSON"
        ) from exc

    if not isinstance(body, dict):
        raise DifyResponseError(
            f"dify response error: expected JSON object but got {type(body).__name__}"
        )
    return body


def _raise_if_business_failed(body: dict[str, Any]) -> None:
    api_code = body.get("code")
    if api_code is not None and api_code not in (0, "0", 200, "200"):
        detail = body.get("message") or body.get("msg") or body
        raise DifyResponseError(
            f"dify response error: api code={api_code} detail={detail}"
        )

    if body.get("error"):
        raise DifyResponseError(
            "dify response error: error field is present in response body"
        )


def upload_csv_to_dify(
    target: DifyTargetConfig,
    csv_path: Path,
    *,
    upload_filename: str | None = None,
) -> UploadResult:
    csv_bytes = _read_csv_bytes(csv_path)
    filename = (upload_filename or "").strip() or csv_path.name
    url = (
        f"{target.api_base_v1}/datasets/"
        f"{target.dataset_id}/document/create-by-file"
    )
    data_payload = json.dumps(
        {
            "indexing_technique": "high_quality",
            "doc_form": "text_model",
            "process_rule": {"mode": "automatic"},
        },
        ensure_ascii=False,
    )

    try:
        with httpx.Client(
            verify=target.http_verify,
            timeout=target.timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {target.api_key}"},
                files={"file": (filename, csv_bytes, "text/csv")},
                data={"data": data_payload},
            )
    except httpx.RequestError as exc:
        raise DifyRequestError(
            f"dify request error: upload request failed: {exc}"
        ) from exc

    if response.status_code >= 400:
        server_hint = ""
        hdrs = getattr(response, "headers", None)
        ct = ""
        if hdrs is not None:
            try:
                ct = (hdrs.get("content-type") or "").lower()
            except Exception:
                ct = ""
        if "application/json" in ct:
            try:
                err_body = response.json()
                if isinstance(err_body, dict):
                    code = err_body.get("code")
                    msg = err_body.get("message")
                    if code is not None or msg is not None:
                        server_hint = f"; server={code}: {msg}"
            except (AttributeError, json.JSONDecodeError, ValueError, TypeError):
                pass
        raise DifyRequestError(
            f"dify request error: upload failed with status={response.status_code} "
            f"reason={response.reason_phrase}{server_hint}"
        )

    body = _parse_json_body(response)
    _raise_if_business_failed(body)

    document_id = _extract_document_id(body)
    raw_batch = body.get("batch")
    batch = "" if raw_batch is None else str(raw_batch).strip()
    if not batch:
        raise DifyResponseError("dify response error: missing batch in response body")

    return UploadResult(
        dataset_id=target.dataset_id,
        document_id=document_id,
        batch=batch,
        response_body=body,
    )
