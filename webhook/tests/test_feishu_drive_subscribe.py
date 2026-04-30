from unittest.mock import patch

from webhook_cursor_executor.feishu_drive_subscribe import (
    DRIVE_SUBSCRIBE_FILE_TYPES,
    resolve_subscribe_file_type_for_created_in_folder,
    subscribe_file_type_fallback,
)


def test_resolve_subscribe_prefers_event_file_type() -> None:
    assert (
        resolve_subscribe_file_type_for_created_in_folder(
            {"file_type": "sheet"},
            "drive_file",
            "docx",
        )
        == "sheet"
    )


def test_resolve_subscribe_cloud_docx_fallback_docx() -> None:
    assert (
        resolve_subscribe_file_type_for_created_in_folder(
            {},
            "cloud_docx",
            None,
        )
        == "docx"
    )


def test_resolve_subscribe_uses_doc_type_when_event_missing() -> None:
    assert (
        resolve_subscribe_file_type_for_created_in_folder(
            {},
            "drive_file",
            "file",
        )
        == "file"
    )


def test_subscribe_file_type_fallback() -> None:
    assert subscribe_file_type_fallback("cloud_docx", None) == "docx"
    assert subscribe_file_type_fallback("drive_file", "bitable") == "bitable"
    assert subscribe_file_type_fallback("drive_file", None) is None


def test_drive_subscribe_types_contains_api_enums() -> None:
    assert "docx" in DRIVE_SUBSCRIBE_FILE_TYPES
    assert "slides" in DRIVE_SUBSCRIBE_FILE_TYPES
    assert "folder" not in DRIVE_SUBSCRIBE_FILE_TYPES


@patch("webhook_cursor_executor.feishu_drive_subscribe.urlopen")
@patch("webhook_cursor_executor.feishu_drive_subscribe._get_tenant_access_token")
def test_event_driven_posts_subscribe(mock_tenant, mock_urlopen) -> None:
    mock_tenant.return_value = "tok"
    cm = mock_urlopen.return_value.__enter__.return_value
    cm.read.return_value = b'{"code":0,"msg":"ok"}'

    from webhook_cursor_executor.feishu_drive_subscribe import (
        event_driven_per_doc_subscribe,
    )
    from webhook_cursor_executor.settings import ExecutorSettings

    event_driven_per_doc_subscribe(
        ExecutorSettings(
            feishu_encrypt_key="",
            feishu_verification_token="",
            feishu_app_id="a",
            feishu_app_secret="b",
        ),
        "FILE_TOKEN_X",
        "docx",
    )
    assert mock_urlopen.called
    req = mock_urlopen.call_args[0][0]
    url = req.full_url.lower()
    assert "open.feishu.cn/open-apis/drive/v1/files/" in url
    assert "file_token_x" in url
    assert "file_type=docx" in url
