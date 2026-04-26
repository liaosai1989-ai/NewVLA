import json

import httpx
import pytest

from dify_upload.config import DifyTargetConfig
from dify_upload.upload import (
    DifyRequestError,
    DifyResponseError,
    UploadResult,
    upload_csv_to_dify,
)


class StaticClient:
    response = None
    error = None
    last_init = None
    last_post = None

    def __init__(self, *, verify, timeout, follow_redirects):
        type(self).last_init = {
            "verify": verify,
            "timeout": timeout,
            "follow_redirects": follow_redirects,
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def post(self, url, *, headers, files, data):
        type(self).last_post = {
            "url": url,
            "headers": headers,
            "files": files,
            "data": data,
        }
        if type(self).error is not None:
            raise type(self).error
        return type(self).response


def test_upload_posts_fixed_contract_and_returns_structured_result(tmp_path, monkeypatch):
    csv_path = tmp_path / "qa.csv"
    csv_path.write_bytes(b"question,answer\nq,a\n")

    StaticClient.error = None
    StaticClient.response = type(
        "SuccessResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {"document": {"id": "doc_123"}, "batch": "batch_123"},
        },
    )()
    monkeypatch.setattr("dify_upload.upload.httpx.Client", StaticClient)

    result = upload_csv_to_dify(
        DifyTargetConfig(
            api_base="https://dify.example.com/",
            api_key="dataset-key",
            dataset_id="dataset-123",
            http_verify=False,
            timeout_seconds=12.5,
        ),
        csv_path,
        upload_filename="upload.csv",
    )

    assert StaticClient.last_init == {
        "verify": False,
        "timeout": 12.5,
        "follow_redirects": False,
    }
    assert StaticClient.last_post["url"] == (
        "https://dify.example.com/v1/datasets/dataset-123/document/create-by-file"
    )
    assert StaticClient.last_post["headers"]["Authorization"] == "Bearer dataset-key"
    assert StaticClient.last_post["files"]["file"] == (
        "upload.csv",
        b"question,answer\nq,a\n",
        "text/csv",
    )
    assert json.loads(StaticClient.last_post["data"]["data"]) == {
        "indexing_technique": "high_quality",
        "doc_form": "text_model",
        "process_rule": {"mode": "automatic"},
    }
    assert result == UploadResult(
        dataset_id="dataset-123",
        document_id="doc_123",
        batch="batch_123",
        response_body={"document": {"id": "doc_123"}, "batch": "batch_123"},
    )


def test_upload_uses_trimmed_target_values_and_accepts_zero_batch(tmp_path, monkeypatch):
    csv_path = tmp_path / "qa.csv"
    csv_path.write_bytes(b"question,answer\nq,a\n")

    StaticClient.error = None
    StaticClient.response = type(
        "ZeroBatchResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {"document": {"id": "doc_trimmed"}, "batch": 0},
        },
    )()
    monkeypatch.setattr("dify_upload.upload.httpx.Client", StaticClient)

    result = upload_csv_to_dify(
        DifyTargetConfig(
            api_base=" https://dify.example.com/ ",
            api_key=" dataset-key ",
            dataset_id=" dataset-123 ",
        ),
        csv_path,
    )

    assert StaticClient.last_post["url"] == (
        "https://dify.example.com/v1/datasets/dataset-123/document/create-by-file"
    )
    assert StaticClient.last_post["headers"]["Authorization"] == "Bearer dataset-key"
    assert result.dataset_id == "dataset-123"
    assert result.batch == "0"


def test_upload_accepts_fallback_document_path(tmp_path, monkeypatch):
    csv_path = tmp_path / "qa.csv"
    csv_path.write_bytes(b"question,answer\nq,a\n")

    StaticClient.error = None
    StaticClient.response = type(
        "FallbackResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {
                "data": {"document": {"id": "doc_fallback"}},
                "batch": "batch_fallback",
            },
        },
    )()
    monkeypatch.setattr("dify_upload.upload.httpx.Client", StaticClient)

    result = upload_csv_to_dify(
        DifyTargetConfig(
            api_base="https://dify.example.com",
            api_key="dataset-key",
            dataset_id="dataset-123",
        ),
        csv_path,
    )

    assert result.document_id == "doc_fallback"
    assert result.batch == "batch_fallback"


def test_upload_rejects_missing_or_non_csv_file(tmp_path):
    target = DifyTargetConfig(
        api_base="https://dify.example.com",
        api_key="dataset-key",
        dataset_id="dataset-123",
    )

    with pytest.raises(DifyRequestError, match="file does not exist"):
        upload_csv_to_dify(target, tmp_path / "missing.csv")

    txt_path = tmp_path / "qa.txt"
    txt_path.write_bytes(b"question,answer\nq,a\n")
    with pytest.raises(DifyRequestError, match="file is not csv"):
        upload_csv_to_dify(target, txt_path)


def test_upload_wraps_request_and_http_failures(tmp_path, monkeypatch):
    csv_path = tmp_path / "qa.csv"
    csv_path.write_bytes(b"question,answer\nq,a\n")
    monkeypatch.setattr("dify_upload.upload.httpx.Client", StaticClient)

    request = httpx.Request("POST", "https://dify.example.com")
    StaticClient.response = None
    StaticClient.error = httpx.ConnectTimeout("boom", request=request)
    with pytest.raises(DifyRequestError, match="upload request failed"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.error = None
    StaticClient.response = type(
        "UnauthorizedResponse",
        (),
        {"status_code": 401, "reason_phrase": "Unauthorized"},
    )()
    with pytest.raises(DifyRequestError, match="status=401 reason=Unauthorized"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )


def test_upload_rejects_invalid_response_shapes_and_business_failures(tmp_path, monkeypatch):
    csv_path = tmp_path / "qa.csv"
    csv_path.write_bytes(b"question,answer\nq,a\n")
    monkeypatch.setattr("dify_upload.upload.httpx.Client", StaticClient)
    StaticClient.error = None

    StaticClient.response = type(
        "JsonDecodeResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: (_ for _ in ()).throw(json.JSONDecodeError("bad", "x", 0)),
        },
    )()
    with pytest.raises(DifyResponseError, match="response is not valid JSON"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.response = type(
        "ValueErrorResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: (_ for _ in ()).throw(ValueError("bad json")),
        },
    )()
    with pytest.raises(DifyResponseError, match="response is not valid JSON"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.response = type(
        "ArrayResponse",
        (),
        {"status_code": 200, "reason_phrase": "OK", "json": lambda self: []},
    )()
    with pytest.raises(DifyResponseError, match="expected JSON object but got list"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.response = type(
        "CodeResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {"code": 123, "message": "process_rule is required"},
        },
    )()
    with pytest.raises(DifyResponseError, match="api code=123"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.response = type(
        "ErrorResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {"error": "blocked", "batch": "x", "document": {"id": "y"}},
        },
    )()
    with pytest.raises(DifyResponseError, match="error field is present"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.response = type(
        "DocumentMissingResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {"batch": "batch_only"},
        },
    )()
    with pytest.raises(DifyResponseError, match="missing document_id"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )

    StaticClient.response = type(
        "BatchMissingResponse",
        (),
        {
            "status_code": 200,
            "reason_phrase": "OK",
            "json": lambda self: {"document": {"id": "doc_123"}},
        },
    )()
    with pytest.raises(DifyResponseError, match="missing batch"):
        upload_csv_to_dify(
            DifyTargetConfig(
                api_base="https://dify.example.com",
                api_key="dataset-key",
                dataset_id="dataset-123",
            ),
            csv_path,
        )
