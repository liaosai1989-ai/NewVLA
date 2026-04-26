from pathlib import Path

import pytest

from feishu_fetch import FeishuFetchError, FeishuFetchRequest, FeishuFetchResult


def test_request_validation_and_error_contract(tmp_path):
    ok = FeishuFetchRequest(
        ingest_kind="cloud_docx",
        document_id="doccnxxxx",
        output_dir=tmp_path,
        title_hint="Weekly Sync",
    )
    assert ok.ingest_kind == "cloud_docx"
    assert ok.output_dir == tmp_path

    result = FeishuFetchResult(
        artifact_path=str(tmp_path / "weekly-sync.xml"),
        ingest_kind="cloud_docx",
        title="Weekly Sync",
    )
    assert result.title == "Weekly Sync"

    with pytest.raises(FeishuFetchError) as missing_document:
        FeishuFetchRequest(
            ingest_kind="cloud_docx",
            output_dir=tmp_path,
        )
    assert missing_document.value.code == "request_error"
    assert "必须提供 document_id" in str(missing_document.value)

    with pytest.raises(FeishuFetchError) as missing_drive_fields:
        FeishuFetchRequest(
            ingest_kind="drive_file",
            output_dir=tmp_path,
            file_token="filecnxxxx",
        )
    assert missing_drive_fields.value.code == "request_error"
    assert "必须同时提供 file_token 和 doc_type" in str(missing_drive_fields.value)

    with pytest.raises(FeishuFetchError) as only_document_id:
        FeishuFetchRequest(
            ingest_kind="drive_file",
            document_id="doccnxxxx",
            output_dir=tmp_path,
        )
    assert only_document_id.value.code == "request_error"
    assert "不能把 document_id 当作 drive_file 的兜底输入" in str(only_document_id.value)

    with pytest.raises(FeishuFetchError) as unsupported_doc_type:
        FeishuFetchRequest(
            ingest_kind="drive_file",
            file_token="filecnxxxx",
            doc_type="slides",
            output_dir=tmp_path,
        )
    assert unsupported_doc_type.value.code == "request_error"
    assert "doc_type 不在第一版支持范围内" in str(unsupported_doc_type.value)


def test_error_string_returns_llm_message():
    error = FeishuFetchError(
        code="dependency_error",
        llm_message="飞书正文抓取失败：找不到 lark-cli。\n处理建议：先确认本机已安装并可直接执行 lark-cli。",
        detail={"command": ["lark-cli", "--help"]},
    )

    assert str(error) == error.llm_message
    assert error.detail["command"] == ["lark-cli", "--help"]


@pytest.mark.parametrize("bad_timeout", [0, -1, float("nan")])
def test_request_rejects_non_positive_or_non_finite_timeout(tmp_path, bad_timeout):
    with pytest.raises(FeishuFetchError) as exc:
        FeishuFetchRequest(
            ingest_kind="cloud_docx",
            document_id="doccnxxxx",
            output_dir=tmp_path,
            timeout_seconds=bad_timeout,
        )

    assert exc.value.code == "request_error"
    assert "timeout_seconds" in str(exc.value)


def test_package_root_exports_stable_public_api():
    assert FeishuFetchRequest.__name__ == "FeishuFetchRequest"
    assert FeishuFetchResult.__name__ == "FeishuFetchResult"
    assert FeishuFetchError.__name__ == "FeishuFetchError"
