from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .config import DifyUploadConfig
from .http_port import SimpleHttpPort

log = logging.getLogger(__name__)


def _document_id_from_body(body: dict[str, Any]) -> str | None:
    def _pick(doc: Any) -> str | None:
        if not isinstance(doc, dict):
            return None
        raw = doc.get("id")
        if raw is None:
            return None
        text = str(raw).strip()
        return text or None

    picked = _pick(body.get("document"))
    if picked:
        return picked

    data = body.get("data")
    if isinstance(data, dict):
        picked = _pick(data.get("document"))
        if picked:
            return picked

    return None


def upload_csv_document(
    config: DifyUploadConfig,
    csv_path: Path,
    *,
    http: SimpleHttpPort,
    dataset_id: str | None = None,
    api_key: str | None = None,
    upload_filename: str | None = None,
) -> dict[str, Any]:
    ds = (dataset_id or config.dataset_id or "").strip()
    if not ds:
        raise RuntimeError("dify dataset_id is empty")

    key = (api_key or config.api_key or "").strip()
    if not key:
        raise RuntimeError("dify api_key is empty")

    url = f"{config.api_base_v1}/datasets/{ds}/document/create-by-file"
    headers = {"Authorization": f"Bearer {key}"}
    data_payload = json.dumps(
        {
            "indexing_technique": "high_quality",
            "doc_form": "text_model",
            "process_rule": {"mode": "automatic"},
        },
        ensure_ascii=False,
    )
    fname = (upload_filename or "").strip() or csv_path.name
    files = {"file": (fname, csv_path.read_bytes(), "text/csv")}

    response = http.request(
        "POST",
        url,
        headers=headers,
        files=files,
        data={"data": data_payload},
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"dify upload permanent: status={response.status_code} reason={response.reason_phrase}"
        )

    try:
        body = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError("dify upload: response is not JSON") from exc

    if not isinstance(body, dict):
        raise RuntimeError(f"dify upload: unexpected JSON type {type(body).__name__}")

    api_code = body.get("code")
    if api_code is not None and api_code not in (0, "0", 200, "200"):
        detail = body.get("message") or body.get("msg") or body
        raise RuntimeError(f"dify api error code={api_code}: {detail}")

    if body.get("error"):
        raise RuntimeError(f"dify error: {body}")

    batch = body.get("batch")
    batch_s = str(batch) if batch is not None else None
    doc_id = _document_id_from_body(body)

    if not doc_id or not batch_s:
        log.warning(
            "dify upload http_ok but missing document_id or batch file=%s dataset_id=%s",
            fname,
            ds,
        )

    return {
        "dataset_id": ds,
        "document_id": doc_id,
        "batch": batch_s,
    }
